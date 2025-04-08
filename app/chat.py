# app/chat.py

from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import ChatSession, ChatMessage
import requests
import json

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/', methods=['GET'])
@login_required
def index():
    # List previous chat sessions for the user
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    return render_template('chat.html', sessions=sessions)

@chat_bp.route('/session/new', methods=['GET', 'POST'])
@login_required
def new_session():
    from app.models import Recording, ChatSession  # import if not already
    if request.method == 'POST':
        title = request.form.get('title') or "Chat Session"
        # Grab selected recordings (list of IDs)
        selected_recording_ids = request.form.getlist('recordings')  # e.g. [ "12", "13" ]

        new_session = ChatSession(user_id=current_user.id, title=title)

        # Convert IDs to Recording objects
        for rid in selected_recording_ids:
            recording = Recording.query.filter_by(id=rid, user_id=current_user.id).first()
            if recording:
                new_session.recordings.append(recording)

        db.session.add(new_session)
        db.session.commit()
        return redirect(url_for('chat.view_session', session_id=new_session.id))
    
    # If GET, show the form with a list of the user's recordings
    user_recordings = Recording.query.filter_by(user_id=current_user.id).order_by(Recording.timestamp.desc()).all()
    return render_template('new_chat.html', user_recordings=user_recordings)

@chat_bp.route('/session/<int:session_id>', methods=['GET'])
@login_required
def view_session(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash("Permission denied.", "danger")
        return redirect(url_for('chat.index'))
    # Load messages for this session in chronological order
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.timestamp.asc()).all()
    return render_template('chat_session.html', session=session, messages=messages)

@chat_bp.route('/session/<int:session_id>/send', methods=['POST'])
@login_required
def send_message(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied.'}), 403

    user_message = request.form.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided.'}), 400

    # Save the user’s message
    new_msg = ChatMessage(session_id=session.id, role='user', content=user_message)
    db.session.add(new_msg)
    db.session.commit()

    # Build base conversation history
    history = []
    history.append({
        'role': 'system',
        'content': (
            "You are Memory AI, an advanced assistant that has access to the user’s selected transcripts. "
            "Provide clear, factual, and helpful answers by referencing or summarizing these transcripts "
            "when relevant. If uncertain, ask clarifying questions. Focus on accuracy and completeness."
        )
    })

    # Retrieve the transcripts specifically linked to this chat session
    transcripts = session.recordings

    # If any transcripts are attached, add them in full to the system message
    if transcripts:
        full_transcript_text = ""
        for rec in transcripts:
            full_transcript_text += (
                f"=== Transcript from {rec.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
                f"{rec.transcript}\n\n"
            )

        history.append({
            'role': 'system',
            'content': (
                "Below are the full transcripts the user has selected. "
                "Reference these as needed:\n\n" + full_transcript_text
            )
        })

    # Now add all previous conversation messages for context
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.timestamp.asc()).all()
    for msg in messages:
        history.append({'role': msg.role, 'content': msg.content})

    # Send the entire conversation to Ollama
    ollama_url = current_app.config.get("OLLAMA_API_URL") + "/chat"
    payload = {
        "model": current_app.config.get("OLLAMA_MODEL"),
        "messages": history,
        "stream": False
    }
    try:
        r = requests.post(ollama_url, json=payload, timeout=30)
        r.raise_for_status()
        api_response = r.json()
        reply = api_response.get("message", {}).get("content", "No response")
    except Exception as e:
        reply = f"Error: {str(e)}"

    # Save assistant’s reply
    new_reply = ChatMessage(session_id=session.id, role='assistant', content=reply)
    db.session.add(new_reply)
    db.session.commit()

    return jsonify({'reply': reply})

@chat_bp.route('/session/with-recording/<int:recording_id>', methods=['POST'])
@login_required
def session_with_recording(recording_id):
    from app.models import Recording, ChatSession
    import requests

    recording = Recording.query.get_or_404(recording_id)
    
    # Ensure the current user owns this recording
    if recording.user_id != current_user.id:
        return jsonify({"error": "Permission denied."}), 403

    # Reuse session if one already references this recording
    session = (
        ChatSession.query
        .filter(ChatSession.user_id == current_user.id)
        .join(ChatSession.recordings)
        .filter_by(id=recording.id)
        .first()
    )
    if session:
        # Session already exists, just return its ID
        return jsonify({"session_id": session.id})

    # Otherwise, create a NEW session and generate a short title based on the transcript
    # Limit the text we send to Ollama if the transcript is huge
    transcript_excerpt = recording.transcript[:2000]
    prompt = (
        "Generate a concise 5-word-or-less title (just the title, no extra text) for a conversation "
        f"based on the following transcript:\n\n{transcript_excerpt}\n\n"
        "Title:"
    )

    ollama_url = current_app.config.get("OLLAMA_API_URL") + "/generate"
    ollama_model = current_app.config.get("OLLAMA_MODEL")
    payload = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False
    }

    try:
        r = requests.post(ollama_url, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        generated_title = data.get("response", "").strip()
        if not generated_title:
            generated_title = "Chat about Recording"
    except Exception as e:
        current_app.logger.error(f"Failed to generate chat title with Ollama: {e}")
        generated_title = "Chat about Recording"

    # Create the new session with the GPT-generated title
    new_session = ChatSession(user_id=current_user.id, title=generated_title)
    new_session.recordings.append(recording)
    db.session.add(new_session)
    db.session.commit()

    return jsonify({"session_id": new_session.id})

@chat_bp.route('/session/<int:session_id>/messages', methods=['GET'])
@login_required
def get_session_messages(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Permission denied."}), 403

    messages_query = ChatMessage.query \
        .filter_by(session_id=session.id) \
        .order_by(ChatMessage.timestamp.asc())
    messages = messages_query.all()

    results = []
    for m in messages:
        results.append({
            "id": m.id,
            "role": m.role,
            "content": m.content
        })
    return jsonify({"messages": results})
