from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime
import json
import secrets
import os
import requests
import base64


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/home')
def home():
    current_year = datetime.now().year

    return render_template(
        'index.html',
        current_year=current_year,
        user=current_user
    )


@main_bp.route('/about')
def about():
    current_year = datetime.now().year

    return render_template(
        'about.html',
        user=current_user,
        current_year=current_year
    )


# ============================================================
# CAREERS
# ============================================================

@main_bp.route('/careers')
def careers():
    return render_template(
        'tcai_career_application.html'
    )


@main_bp.route('/api/career', methods=['POST'])
def career_application():
    try:
        # Get JSON submitted by the career application page
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                'success': False,
                'message': 'Invalid application data.'
            }), 400

        # Career Apps Script configuration
        apps_script_url = os.getenv(
            'TCAI_CAREER_APPS_SCRIPT_URL'
        )

        api_key = os.getenv(
            'TCAI_CAREER_API_KEY'
        )

        if not apps_script_url:
            return jsonify({
                'success': False,
                'message': 'Career Apps Script URL is not configured.'
            }), 500

        if not api_key:
            return jsonify({
                'success': False,
                'message': 'Career Apps Script API key is not configured.'
            }), 500

        # Add the private API key server-side.
        # It is NOT exposed to the browser.
        data['apiKey'] = api_key

        # Send application to Google Apps Script
        response = requests.post(
            apps_script_url,
            json=data,
            timeout=120
        )

        # Try to read Apps Script JSON response
        try:
            result = response.json()
        except ValueError:
            print(
                'Career Apps Script returned non-JSON response:',
                response.status_code,
                response.text[:1000]
            )

            return jsonify({
                'success': False,
                'message': 'Invalid response from application service.'
            }), 502

        # Apps Script returned an HTTP error
        if not response.ok:
            return jsonify({
                'success': False,
                'message': result.get(
                    'message',
                    'Application submission failed.'
                )
            }), 502

        # Return Apps Script result to browser
        return jsonify(result), 200

    except requests.RequestException as e:
        print(
            'Career Apps Script connection error:',
            e
        )

        return jsonify({
            'success': False,
            'message': 'Unable to connect to the application service.'
        }), 502

    except Exception as e:
        print(
            'Career application error:',
            e
        )

        return jsonify({
            'success': False,
            'message': 'Unable to process application.'
        }), 500


# ============================================================
# ONBOARDING
# ============================================================

@main_bp.route('/onboarding')
@login_required
def onboarding():
    return render_template(
        'onboarding.html',
        user=current_user
    )


@main_bp.route('/api/onboarding', methods=['POST'])
@login_required
def submit_onboarding():
    try:
        # Get onboarding JSON data
        payload = request.form.get('payload')

        if not payload:
            return jsonify({
                'success': False,
                'message': 'Onboarding data is missing.'
            }), 400

        data = json.loads(payload)

        # Generate reference number on the server
        now = datetime.now()

        reference_number = (
            f"TCAI-ONB-{now.strftime('%Y%m%d')}-"
            f"{secrets.randbelow(9000) + 1000}"
        )

        submitted_at = now.isoformat()

        # Candidate information sent by onboarding form
        candidate = data.get(
            'candidate',
            {}
        )

        # Make sure logged-in employee email is available
        if not candidate.get('email'):
            candidate['email'] = current_user.email

        # Prepare uploaded documents
        documents = {}

        for field_name, uploaded_file in request.files.items():

            if (
                not uploaded_file
                or not uploaded_file.filename
            ):
                continue

            # Read file
            file_bytes = uploaded_file.read()

            # Convert file to Base64
            file_base64 = base64.b64encode(
                file_bytes
            ).decode('utf-8')

            documents[field_name] = {
                'name': uploaded_file.filename,
                'type': uploaded_file.content_type,
                'size': len(file_bytes),
                'base64': file_base64
            }

        # Get onboarding Apps Script configuration
        apps_script_url = os.getenv(
            'TCAI_ONBOARDING_APPS_SCRIPT_URL'
        )

        api_key = os.getenv(
            'TCAI_ONBOARDING_API_KEY'
        )

        if not apps_script_url:
            return jsonify({
                'success': False,
                'message': 'Apps Script URL is not configured.'
            }), 500

        if not api_key:
            return jsonify({
                'success': False,
                'message': 'Apps Script API key is not configured.'
            }), 500

        # Data sent from Flask to Google Apps Script
        apps_script_payload = {
            'apiKey': api_key,
            'referenceNumber': reference_number,
            'submittedAt': submitted_at,
            'candidate': candidate,
            'documents': documents
        }

        # Send onboarding data to Google Apps Script
        apps_script_response = requests.post(
            apps_script_url,
            json=apps_script_payload,
            timeout=120
        )

        # Try to read Apps Script response
        try:
            apps_script_result = (
                apps_script_response.json()
            )
        except Exception:
            apps_script_result = {}

        # Apps Script rejected submission
        if (
            apps_script_response.status_code != 200
            or not apps_script_result.get('success')
        ):
            print(
                'Apps Script error:',
                apps_script_response.status_code,
                apps_script_response.text
            )

            return jsonify({
                'success': False,
                'message': apps_script_result.get(
                    'message',
                    'Google Sheets submission failed.'
                )
            }), 500

        # Everything succeeded
        return jsonify({
            'success': True,
            'message': 'Onboarding submitted successfully.',
            'referenceNumber': reference_number,
            'submittedAt': submitted_at
        }), 200

    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'message': 'Invalid onboarding data.'
        }), 400

    except requests.RequestException as e:
        print(
            'Apps Script connection error:',
            e
        )

        return jsonify({
            'success': False,
            'message': 'Could not connect to Google Sheets.'
        }), 502

    except Exception as e:
        print(
            'Onboarding submission error:',
            e
        )

        return jsonify({
            'success': False,
            'message': 'Failed to process onboarding submission.'
        }), 500