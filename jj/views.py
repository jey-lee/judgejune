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
from django.views.decorators.http import require_GET
from openai import OpenAI


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
    user = request.user
    sessions = Session.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'member_profile.html', {
        'user': user,
        'sessions': sessions})

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
        event_type = request.GET.get('event_type')
        name = request.GET.get('name')
        resolution = request.GET.get('resolution')

        session = Session(created_by=request.user, name=name, resolution=resolution, event_type=event_type)
        session.save()

        # Redirect to the session edit page or another appropriate page
        return redirect('edit_session', session.id)

    return render(request, 'create_session.html')

@csrf_exempt
def create_new_session(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:

            data = json.loads(request.body)
            
            event_type = data.get('event_type')
            name = data.get('name')
            resolution = data.get('resolution')

            if name and resolution and event_type:
                # Create your session here
                # Replace `Session.objects.create` with your actual model and logic
                session = Session.objects.create(created_by=request.user, name=name, resolution=resolution, event_type=event_type)
                return JsonResponse({
                    'success': True,
                    'event_type': session.event_type,
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

        content = f"Resolution is : {data['resolution']}\n"
        content += f"Transcription is : {data['transcription']}\n"

        event_type = data['event_type']

        prompt = generate_prompt(event_type) + content

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

def generate_prompt(event_type):
     prompt = "Given the following transcript of a Public Forum Debate round, evaluate the argument based on the following criteria:\n"

     if event_type == 'Public Forum':
         prompt += "1. Argumentation is focused on the resolution, where the Affirmative side is in support of said resolution and the Negative side is in opposition\n"
         prompt += "2. Each speech presents independent argumentation for each side, refutations against the opposing side, defenses against such refutations, and comparisons between the implications of each argument\n"
         prompt += "3. The round is structured by two constructives, two rebuttals, two summaries, and two final foci; disregard any new evidence or arguments presented in the last 4 speeches: these speeches should be cross applications or clarifications of arguments already made in the round\n"
         prompt += "4. Upon completion, provide feedback for each speech, give a final decision on the side that won the debate, and explain your rationale for the decision\n"
         prompt += "5. There should be specific arguments that you felt compelled to vote on for a side to win the round, no decision should be made for general strategy or eloquence\n"
     elif event_type == 'Parliamentary Debate':
         prompt += "1. The round is structured by four constructives and two rebuttals: constructives are speeches in which debates occur with new information and responses and rebuttals are speeches in which the main issues of the debate are weighed to show who wins. New information is not allowed in rebuttal speeches.\n"
         prompt += "2. The format of the round is first affirmative construction (7 minutes), first negative constructive (8 minutes), second affirmative constructive (8 minutes), second negative constructive (8 minutes), negative rebuttal (4 minutes), affirmative rebuttal (5 minutes).\n"
         prompt += "3. POIs, which are questions that examine the cases of the speaking side can be asked during constructive speeches. These interrupt the time and continue within the time. They are not allowed in the rebuttal speeches.\n"
         prompt += "4. POOs, which pause time are used to point out new information being brought up in the rebuttal speeches, which violates the rules. It is up to you, the judge, to determine whether this information was previously mentioned or is new.\n"
         prompt += "5. The criterion on which the round should be weighed will be provided by the debaters, whether it be a fact, policy, or value round (the definition of these rounds will also be provided). Please go with the framework that the debaters agree on, and if the weighing mechanism is contested, choose what seems most logical to you based on their arguments.\n"
         prompt += "6. Although some evidence can be cited, unless contested, all points provided by debaters should be accepted as fact. However, detailed statistics and numbers should enhance the validity of points proposed by either side.\n"
         prompt += "7. In Parli, the debaters must point out anything for it to be valid, so only take rebuttals and dropped points if the debaters point them out.\n"
         prompt += "8. At the end of the round, please look over everything that has been said and make a decision. Give feedback on missed points of the debate, good areas, and analyze each speech so that speakers can see what they did good and what they can do better.\n"
    
     prompt += "The results should have three main sections. 1.Summary of the round. 2.Decision and reason for decision and 3.Feedback to each team"

     return prompt

# Function to call the OpenAI API for fast, high-quality ballot evaluation
def call_openai_api(prompt, response_list):
    try:
        try:
            logger.info("Generating ballot decision using GPT-4o for fast response...")
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "developer", "content": "You are an expert, unbiased debate judge evaluating round ballots."},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=2000,
            )
        except Exception as primary_err:
            logger.warning(f"Primary model call failed ({primary_err}). Falling back to gpt-4o-mini.")
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "developer", "content": "You are an expert, unbiased debate judge evaluating round ballots."},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=2000,
            )
        result = response.choices[0].message.content
        response_list.append(result)
    except Exception as e:
        logger.error(f"Error generating ballot: {e}")
        response_list.append(f"Error: {e}")

@csrf_exempt
def sessiontoken_view(request):
    if request.method != "GET":
        return HttpResponseBadRequest("Invalid request method.")

    # Retrieve your OpenAI API key from the environment
    openai_api_key = openai.api_key
    print(openai_api_key)

    if not openai_api_key:
        logger.error("OpenAI API key not configured.")
        return JsonResponse({"error": "OpenAI API key not configured."}, status=500)

    url = "https://api.openai.com/v1/realtime/transcription_sessions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload = {
        "input_audio_transcription": {
            "model": "gpt-4o-transcribe",
            "prompt": "",
            "language": "en"
        },
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        },
        "input_audio_noise_reduction": {
            "type": "near_field"
        },
        "include": ["item.input_audio_transcription.logprobs"],
        "input_audio_format": "pcm16"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error("OpenAI API error: %s", response.text)
        response.raise_for_status()
    except requests.RequestException as e:
        error_details = response.text if response is not None else str(e)
        logger.exception("Failed to create transcription session:")
        return JsonResponse({"error": "Failed to create transcription session", "details": error_details}, status=500)

    return JsonResponse(response.json())


@require_GET
def realtime_token(request):
    cartesia_key = getattr(settings, 'CARTESIA_API_KEY', None) or os.getenv('CARTESIA_API_KEY')
    if not cartesia_key:
        import environ
        env = environ.Env()
        env.read_env(os.path.join(settings.BASE_DIR, '.env'))
        cartesia_key = env('CARTESIA_API_KEY', default=None)

    if not cartesia_key:
        return JsonResponse({"error": "Cartesia API key not configured. Please set CARTESIA_API_KEY in .env"}, status=500)

    url = "https://api.cartesia.ai/access-token"
    headers = {
        "Cartesia-Version": "2026-08-14",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cartesia_key}"
    }
    payload = {
        "grants": {
            "stt": True
        },
        "expires_in": 3600
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return JsonResponse(data)
    except requests.RequestException as e:
        error_details = response.text if response is not None and hasattr(response, 'text') else str(e)
        logger.error(f"Error fetching Cartesia access token: {error_details}")
        return JsonResponse({"error": error_details}, status=500)



def transcription_page(request):
    return render(request, 'oatranscribe.html')

def privacy_view(request):
    return render(request, 'privacy.html')

def terms_view(request):
    return render(request, 'terms.html')

def feedback_view(request):
    return render(request, 'feedback.html')

def support_view(request):
    return render(request, 'support.html')
