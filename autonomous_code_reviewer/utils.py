from django.http import JsonResponse

def get_status_from_code(status_code):
    """
    Returns the status of an HTTP response based on its status code.
    """
    if status_code >= 200 and status_code < 300:
        return 'success'
    elif status_code >= 400 and status_code < 500:
        return 'error'
    else:
        return 'error'

def create_api_response(status_code, message, data=None):
    """
    Returns a standardized JSON API response.
    """
    try:
        response = {
            'status': get_status_from_code(status_code),
            'status_code': status_code,
            'message': message
        }

        if data is not None:
            response['data'] = data

        return JsonResponse(response, status=status_code)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'status_code': 500,
            'message': f"Error creating API response: {e}",
            'data': {'error': str(e)}
        }, status=500)

def create_serializer_response(serializer_errors: dict) -> dict:
    """
    Converts a Django serializer error object into a standardized API response.

    Parameters:
    errors (dict): A Django serializer error object.

    Returns:
    dict: A standardized API response.
    """
    def replace_blank_error(error_message):
        #function to return 'This field is required' if recieve blank or null cases.
        return 'This field is required.' if error_message == 'This field may not be blank.' or error_message == 'This field may not be null.' else error_message
    try:
        fields = [key for key in serializer_errors.keys()]

        errors = {field: {
            'error': ', '.join(map(replace_blank_error, serializer_errors[field]))
        } for field in fields}
        return errors
    except Exception as e:
        print(e)