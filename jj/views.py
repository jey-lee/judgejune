import os
import requests
import logging
import subprocess
import ssl
import openai
import json
import threading

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponseBadRequest, JsonResponse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .forms import SignUpForm
from .models import Session
from .forms import SessionForm
from django.conf import settings
from django.contrib import messages


openai.api_key = settings.OPENAI_KEY

# Set the full path to ffmpeg
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Set up logging
logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')

def landing(request):
    return render(request, 'landing.html')

def transcribe(request):
    return render(request, 'transcribe_audio.html')

@login_required
def profile(request):
    sessions = Session.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'member_profile.html', {'sessions': sessions})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def signup_backup(request):
    print(request.POST)
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')

        # Create a new user
        try:
            user = User.objects.create_user(username=name, email=email, password=password)
            user.save()
            messages.success(request, "Account created successfully!")
            return redirect('login')  # Redirect to login page
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return render(request, 'signup.html')

    return render(request, 'signup.html')  # Render the signup form


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('profile')
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
def create_session(request):
    if request.method == 'POST':
        name = request.GET.get('name')
        resolution = request.GET.get('resolution')

        session = Session(created_by=request.user, name=name, resolution=resolution)
        session.save()

        # Redirect to the session edit page or another appropriate page
        return redirect('edit_session', session.id)

    return render(request, 'create_session.html')

@csrf_exempt
def create_new_session(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            resolution = data.get('resolution')

            if name and resolution:
                # Create your session here
                # Replace `Session.objects.create` with your actual model and logic
                session = Session.objects.create(created_by=request.user, name=name, resolution=resolution)
                return JsonResponse({
                    'success': True,
                    'name': session.name,
                    'resolution': session.resolution,
                    'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'url': f'/session/edit/{session.id}/'
                })
            else:
                return JsonResponse({'success': False, 'error': 'Missing name or resolution'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_exempt
def delete_session(request, session_id):
    if request.method == 'DELETE':
        session = get_object_or_404(Session, id=session_id, created_by=request.user)
        session.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def edit_session(request, session_id=None):

    appId = settings.SYMBL_APPID
    appSecret = settings.SYMBL_APPSECRET

    url = "https://api.symbl.ai/oauth2/token:generate"

    payload = {
        "type": "application",
        "appId": appId,
        "appSecret": appSecret
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    response_data = response.json()
    access_token = response_data['accessToken']

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

    context = {
        'accessToken': access_token,
        'form': form,
        'session': session
    }
    return render(request, 'edit_session.html', context)

@login_required
def generate_response_detail(request):
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

@login_required
def generate_response(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        content = f"Resolution: {data['resolution']}\n"
        content += f"transcription : {data['transcription']}\n"

        prompt = "Please judge the public forum round baed on the full round transcription with resolution" +content
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

        return JsonResponse({'results': response})

    return HttpResponseBadRequest("Invalid request method")

# Function to call the OpenAI API
def call_openai_api(prompt, response_list):
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
        response_list.append(result)
    except Exception as e:
        response_list.append(f"Error: {e}")