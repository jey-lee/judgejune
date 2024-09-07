import os
import whisper
import logging
import subprocess
import ssl
import openai
import json
import threading


from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import Session
from .forms import SessionForm

openai.api_key = 'ADD YOUR KEY'

# Set the full path to ffmpeg
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Load the Whisper model
ssl._create_default_https_context = ssl._create_unverified_context
model = whisper.load_model("base")
# Set up logging
logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('member_overview')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('member_overview')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def member_overview(request):
    sessions = Session.objects.filter(created_by=request.user)
    return render(request, 'member_overview.html', {'sessions': sessions})

@login_required
def session_detail(request, session_id):
    session = get_object_or_404(Session, pk=session_id, created_by=request.user)
    return render(request, 'session_detail.html', {'session': session})

@login_required
def edit_session(request, session_id=None):
    if session_id:
        session = get_object_or_404(Session, pk=session_id, created_by=request.user)
    else:
        session = Session(created_by=request.user)
        session.save()
        return redirect('edit_session', session_id=session.id)

    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            return redirect('edit_session', session_id=session.id)
    else:
        form = SessionForm(instance=session)
    return render(request, 'edit_session.html', {'form': form, 'session': session})

@login_required
def transcribe_audio(request):
    if request.method == 'POST' and request.FILES['audio']:
        try:
            audio_file = request.FILES['audio']
            file_name = default_storage.save(audio_file.name, audio_file)
            file_path = default_storage.path(file_name)

            print(file_name + "/" + file_path)

            # Log the MIME type, file extension, and file size
            mime_type = audio_file.content_type
            file_extension = os.path.splitext(file_name)[1]
            file_size = audio_file.size
            logger.info(f"Received audio file with MIME type: {mime_type}, extension: {file_extension}, size: {file_size} bytes")

            # Print the first few bytes of the file for debugging
            with open(file_path, 'rb') as f:
                file_head = f.read(100)
                logger.info(f"File head: {file_head}")

            # Log additional debug info
            logger.debug(f"File path: {file_path}")
            wav_file_path = file_path + '.wav'
            command = f"ffmpeg -i {file_path} -ac 1 -ar 16000 -f wav {wav_file_path}"
            logger.debug(f"Running command: {command}")

            # Run ffmpeg command and log output
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            logger.debug(f"ffmpeg stdout: {result.stdout}")
            logger.debug(f"ffmpeg stderr: {result.stderr}")

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)

            # Check if the WAV file was created successfully
            if not os.path.exists(wav_file_path):
                raise FileNotFoundError(f"WAV file was not created: {wav_file_path}")

            # Transcribe audio using Whisper
            result = model.transcribe(wav_file_path)
            transcription = result['text']

            # Clean up the stored files
            default_storage.delete(file_name)
            if os.path.exists(wav_file_path):
                os.remove(wav_file_path)

            return JsonResponse({'transcription': transcription})
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr}")
            return JsonResponse({'error': f"ffmpeg error: {e.stderr}"}, status=500)
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def generate_response(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        content = f"Resolution: {data['resolution']}\n"
        content += f"Affirmative Speaker 1: {data['aff_speaker1']}\n"
        content += f"Affirmative Speaker 2: {data['aff_speaker2']}\n"
        content += f"Negative Speaker 1: {data['con_speaker1']}\n"
        content += f"Negative Speaker 2: {data['con_speaker2']}\n"
        content += f"1st Constructive: {data['constructive1']}\n"
        content += f"2nd Constructive: {data['constructive2']}\n"
        content += f"1st Crossfire: {data['crossfire1']}\n"
        content += f"1st Rebuttal: {data['rebuttal1']}\n"
        content += f"2nd Rebuttal: {data['rebuttal2']}\n"
        content += f"2nd Crossfire: {data['crossfire2']}\n"
        content += f"1st Summary: {data['summary1']}\n"
        content += f"2nd Summary: {data['summary2']}\n"
        content += f"Grand Crossfire: {data['grand_crossfire']}\n"
        content += f"1st Final Focus: {data['final_focus1']}\n"
        content += f"2nd Final Focus: {data['final_focus2']}\n"

        print(content)

        prompt = content
        response_list = []

        # Create and start a thread
        api_thread = threading.Thread(target=call_openai_api, args=(prompt, response_list))
        api_thread.start()

        # Wait for the thread to complete
        api_thread.join()

        # Get the result from the response list
        if response_list:
            result = response_list[0]
        else:
            result = "No response received."

        response = result

        return JsonResponse({'response': response})

    return HttpResponseBadRequest("Invalid request method")


# Function to call the OpenAI API
def call_openai_api(prompt, response_list):
    print('### Prompt : ' + prompt)
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a public forum debate judge."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
        )
        result = response.choices[0].message.content
        print(result)
        response_list.append(result)
    except Exception as e:
        response_list.append(f"Error: {e}")