# app/dashboard.py
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import Recording, Todo
from app import db
import os, tempfile, requests, whisper, json, re

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # Archive active todos that are completed and older than 24 hours
    active_todos = Todo.query.filter_by(user_id=current_user.id, archived=False).all()
    for todo in active_todos:
        if todo.completed and datetime.utcnow() - todo.timestamp > timedelta(hours=24):
            todo.archived = True
            current_app.logger.info(f"Archiving Todo {todo.id} - '{todo.description}' (completed over 24 hours)")
    db.session.commit()
    
    active_todos = Todo.query.filter_by(user_id=current_user.id, archived=False).order_by(Todo.timestamp.desc()).all()
    archived_todos = Todo.query.filter_by(user_id=current_user.id, archived=True).order_by(Todo.timestamp.desc()).all()
    recordings = Recording.query.filter_by(user_id=current_user.id).order_by(Recording.timestamp.desc()).all()
    return render_template('dashboard.html', recordings=recordings, todos=active_todos, archived_todos=archived_todos)

@dashboard_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio_file']
    temp_path = os.path.join(tempfile.gettempdir(), audio_file.filename)
    audio_file.save(temp_path)

    # Generate transcript using Whisper
    model = whisper.load_model("base")
    result = model.transcribe(temp_path)
    transcript = result.get("text", "")
    if not transcript.strip():
        return jsonify({
            "transcription": transcript,
            "summary": {"error": "Transcript is empty, cannot generate summary."}
        }), 200

    # First prompt: generate transcript summary.
    prompt = (
        "Please generate a concise summary of the following transcript and extract important notes:\n\n"
        f"{transcript}"
    )
    ollama_url = current_app.config.get("OLLAMA_API_URL") + "/generate"
    ollama_model = current_app.config.get("OLLAMA_MODEL")
    payload = {"model": ollama_model, "prompt": prompt, "stream": False}
    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        ollama_response = response.json()
        summary = ollama_response.get("response", "No response received from Ollama.")
    except Exception as e:
        summary = f"Failed to process transcript with Ollama: {str(e)}"

    # Second prompt: generate TODO items with markers.
    # Ensure the prompt clearly instructs GPT to include the transcript.
    todo_prompt = (
        "Analyze the following transcript and extract any actionable items. "
        "Wrap each actionable item with '#TODO#' markers. For example, if there are two items, "
        "the output should look like: #TODO# Buy groceries #TODO#, #TODO# Email John #TODO#. "
        "Use the transcript provided below:\n\n" + transcript
    )
    current_app.logger.info(f"TODO prompt: {todo_prompt}")
    todo_payload = {"model": ollama_model, "prompt": todo_prompt, "stream": False}
    try:
        todo_response = requests.post(ollama_url, json=todo_payload)
        todo_response.raise_for_status()
        todo_json = todo_response.json()
        raw_todo_response = todo_json.get("response", "")
        current_app.logger.info(f"Raw TODO GPT response: {raw_todo_response}")
        
        # Use regex to capture everything between "#TODO#" markers.
        import re
        raw_items = re.findall(r"#TODO#\s*(.*?)\s*(?=#TODO#|$)", raw_todo_response, re.DOTALL)
        # Filter out any extracted text that appears to be extraneous (e.g., includes 'marker')
        todo_items = [item.strip() for item in raw_items if item.strip() and len(item.strip()) > 3 and "marker" not in item.lower()]
        current_app.logger.info(f"Extracted TODO items: {todo_items}")
    except Exception as e:
        todo_items = []
        current_app.logger.error(f"Failed to extract TODO items: {e}")
        raw_todo_response = ""

    # Save new TODO items if they don't already exist.
    for item in todo_items:
        if item.strip():
            existing = Todo.query.filter_by(user_id=current_user.id, description=item.strip()).first()
            if not existing:
                new_todo = Todo(user_id=current_user.id, description=item.strip())
                db.session.add(new_todo)
                current_app.logger.info(f"Saving new Todo: '{item.strip()}' for user {current_user.id}")
    db.session.commit()

    # Save the recording.
    new_rec = Recording(user_id=current_user.id, transcript=transcript, summary=summary)
    db.session.add(new_rec)
    db.session.commit()

    return jsonify({
         "transcription": transcript,
         "summary": summary,
         "todo_items": todo_items,
         "raw_todo_response": raw_todo_response
    })

@dashboard_bp.route('/recording/<int:recording_id>/view', methods=['GET'])
@login_required
def recording_view(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if recording.user_id != current_user.id:
        flash("Permission denied to view this recording.", "danger")
        return redirect(url_for("dashboard.index"))
    return render_template("recording_view.html", recording=recording)

@dashboard_bp.route('/recording/<int:recording_id>/edit', methods=['GET', 'POST'])
@login_required
def recording_edit(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if recording.user_id != current_user.id:
        flash("Permission denied to edit this recording.", "danger")
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        transcript = request.form.get("transcript")
        summary = request.form.get("summary")
        # Process speaker tags from inputs starting with "speaker_"
        speaker_tags = {}
        for key, value in request.form.items():
            if key.startswith("speaker_"):
                idx = key.split("_")[1]
                if value.strip():
                    speaker_tags[idx] = value.strip()
        recording.transcript = transcript
        recording.summary = summary
        recording.speaker_tags = json.dumps(speaker_tags) if speaker_tags else None
        db.session.commit()
        flash("Recording updated successfully!", "success")
        return redirect(url_for("dashboard.recording_view", recording_id=recording.id))
    return render_template("recording_edit.html", recording=recording)

@dashboard_bp.route('/recording/<int:recording_id>/regenerate', methods=['POST'])
@login_required
def regenerate_summary(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    if recording.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    transcript = request.form.get("transcript")
    if not transcript:
        return jsonify({"error": "Transcript text not provided."}), 400
    prompt = (
        "Please generate a concise summary of the following transcript and extract important notes:\n\n"
        + transcript
    )
    ollama_url = current_app.config.get("OLLAMA_API_URL") + "/generate"
    ollama_model = current_app.config.get("OLLAMA_MODEL")
    payload = {"model": ollama_model, "prompt": prompt, "stream": False}
    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        ollama_response = response.json()
        new_summary = ollama_response.get("response", "No response received from Ollama.")
    except Exception as e:
        new_summary = f"Failed to process transcript with Ollama: {str(e)}"
    recording.summary = new_summary
    db.session.commit()
    return jsonify({"new_summary": new_summary})

# To add a new todo manually.
@dashboard_bp.route('/todo/add', methods=['POST'])
@login_required
def add_todo():
    description = request.form.get("description")
    if not description:
        return jsonify({"error": "Description required."}), 400
    new_todo = Todo(user_id=current_user.id, description=description)
    db.session.add(new_todo)
    db.session.commit()
    return jsonify({"message": "Todo added."}), 200

@dashboard_bp.route('/todo/toggle/<int:todo_id>', methods=['POST'])
@login_required
def toggle_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return jsonify({"error": "Not allowed."}), 403
    todo.completed = not todo.completed
    db.session.commit()
    return jsonify({"message": "Todo updated."}), 200

@dashboard_bp.route('/todo/delete/<int:todo_id>', methods=['DELETE'])
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return jsonify({"error": "Not allowed."}), 403
    db.session.delete(todo)
    db.session.commit()
    return jsonify({"message": "Todo deleted."}), 200

@dashboard_bp.route('/todo/unarchive/<int:todo_id>', methods=['POST'])
@login_required
def unarchive_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return jsonify({"error": "Not allowed."}), 403
    todo.archived = False
    db.session.commit()
    return jsonify({"message": "Todo unarchived."}), 200