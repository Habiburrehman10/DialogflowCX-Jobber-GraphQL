from flask import Flask, request, jsonify
import requests
import json
import os
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Access individual configuration values
os.environ["BEARER_TOKEN"] = os.getenv('BEARER_TOKEN')
# os.environ["X-JOBBER-GRAPHQL-VERSION"] = os.getenv('X-JOBBER-GRAPHQL-VERSION')
os.environ["CLIENT_SECRET"] = os.getenv('CLIENT_SECRET')
os.environ["CLIENT_ID"] = os.getenv('CLIENT_id')
os.environ["REFRESH_TOKEN"] = os.getenv('REFRESH_TOKEN')

graphql_endpoint = 'https://api.getjobber.com/api/graphql'
headers = {
    'Authorization': f'Bearer {os.environ["BEARER_TOKEN"]}',
    'X-JOBBER-GRAPHQL-VERSION': '2024-09-12'
}


def refresh_token():
    api_url = "https://api.getjobber.com/api/oauth/token"
    payload = {
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": os.environ["REFRESH_TOKEN"]
    }
    try:
        response = requests.post(api_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            # Save the new tokens in environment variables
            os.environ["BEARER_TOKEN"] = new_access_token
            os.environ["REFRESH_TOKEN"] = new_refresh_token
            print("Token refreshed successfully!")
            return new_access_token, new_refresh_token
        else:
            print("Failed to refresh token. Status code:", response.status_code)
            return None, None
    except Exception as e:
        print("Error refreshing token:", e)
        return None, None


def get_client_by_phone(phone_number):
    query = """
    query SampleQuery ($searchTerm: String){
      clients(searchTerm: $searchTerm){
        nodes {
          id
          name
          firstName
          phones{
            number
          }
          billingAddress{
            city
            country
            postalCode
            province
            street
            street1
            street2
          }
        }
      }
    }
    """
    
    variables = {
        #"searchTerm": str(phone_number)  # Searching by phone number
        "searchTerm": phone_number
    }

    try:
        response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)
        print(response)

        if response.status_code == 401:
            print(response.status_code)
            # Refresh the token if it has expired
            refresh_token()
            headers["Authorization"] = f'Bearer {os.environ["BEARER_TOKEN"]}'
            response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)

        response = response.json()
        clients = response['data']['clients']['nodes']
        
        # Manually filter clients by phone number
        matching_clients = []
        for client in clients:
            for phone in client.get('phones', []):
                if phone['number'] == phone_number:
                    matching_clients.append(client)
        
        if matching_clients:
            return matching_clients
        else:
            return "No client found with the provided phone number."

        

    except json.JSONDecodeError as e:
        return f"JSON decoding error: {e}"

    except Exception as e:
        return f"An error occurred: {e}"
    
def create_client(first_name,last_name,phone_number,business_name,email,street,city,province,country,postalcode):
    query = """
        mutation CreateClient($input: ClientCreateInput!) {
            clientCreate(input: $input) {
                client {
                    id
                    firstName
                    lastName
                    companyName
                    emails {
                        address
                        description
                        primary
                    }
                    phones {
                        number
                        description
                        primary
                    }
                    properties {
                        address {
                            street1
                            city
                            province
                            postalCode
                            country
                        }
                    }
                }
                userErrors {
                    message
                    path
                }
            }
        }
    """

    variables = {
        "input": {
            "firstName": first_name,
            "lastName": last_name,
            "companyName": business_name,
            "emails": [
                {
                    "description": "MAIN",
                    "primary": True,
                    "address": email
                }
            ],
            "phones": [
                {
                    "description": "MAIN",
                    "primary": True,
                    "number": phone_number
                }
            ],
            "properties": [
                {
                    "address": {
                        "street1": street,
                        "city": city,
                        "province": province,
                        "postalCode": postalcode,
                        "country": country
                    }
                }
            ]
        }
    }


    try:
        # Send request to the GraphQL endpoint
        response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)

        # Check if the token is expired or unauthorized
        if response.status_code == 401:
            refresh_token()  # Refresh the token
            headers["Authorization"] = f'Bearer {os.environ["BEARER_TOKEN"]}'  # Update the authorization header
            response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)

        # Ensure that the response is a valid JSON object
        response_json = response.json()
        print(response_json)  # Debug: Print the response JSON

        # Return the response or handle user errors
        if 'errors' in response_json:
            return {'status': 'error', 'message': response_json['errors']}
        else:
            return {
                'status': 'success',
                'client_info': response_json['data']['clientCreate']['client']
            }

    except json.JSONDecodeError as e:
        return {'status': 'error', 'message': f"JSON decoding error: {str(e)}"}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}




def create_request_including_custom_form(clientId,assessment,work_plan,work_location,treecuttingpermit,service):

    # Construct the GraphQL mutation and input
    query = """
    mutation CreateRequest($input: RequestCreateInput!) {
        requestCreate(input: $input) {
            request {
                id
                title
                client {
                    id
                    firstName
                    lastName
                }
                requestStatus
                createdAt
            }
            userErrors {
                message
                path
            }
        }
    }
    """
    
    # Variables for creating a request with form details
    variables = {
        "input": {
            "clientId": clientId,  # Replace with actual client ID
            "title": service,
            "requestDetails": {
                "form": {
                    "sections": [
                        {
                            "label": "Service Details",
                            "items": [
                                {
                                    "label": "Quel type de service avez vous de besoin?/What kind of service do you need?",
                                    "answerText": service
                                },
                                {
                                    "label": "Indiquer où se situe le ou les arbres et si possible son essence/Please indicate the location of the tree or trees And if possible, its species",
                                    "answerText": work_location
                                },
                                {
                                    "label": "Si c'est pour un abattage, avez-vous déjà votre permis d'abattre?/If it is for a tree removal, do you already have your permit issued by the city?",
                                    "answerText": treecuttingpermit
                                },
                                {
                                    "label": "Quand prévoyez-vous effectuer les travaux?/When do you plan to carry out the work?",
                                    "answerText": work_plan
                                },
                                {
                                    "label": "Est-il possible de faire la soumission en votre absence?/Is it possible to do the submission in your absence?",
                                    "answerText": assessment
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }

    

    # Send the GraphQL request
    try:
        response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)

        if response.status_code == 401:
            refresh_token()  # Refresh the token
            headers["Authorization"] = f'Bearer {os.environ["BEARER_TOKEN"]}'  # Update the authorization header
            response = requests.post(graphql_endpoint, json={'query': query, 'variables': variables}, headers=headers)

        response_json = response.json()

        # Handle response and potential errors
        if 'data' in response_json and 'requestCreate' in response_json['data']:
            request_info = response_json['data']['requestCreate']
            if request_info.get('userErrors'):
                return {'status': 'error', 'message': request_info['userErrors']}
            return {'status': 'success', 'request_info': request_info['request']}
        else:
            return {'status': 'error', 'message': response_json.get('errors', 'Unexpected error occurred')}
    
    except json.JSONDecodeError as e:
        return {'status': 'error', 'message': f"JSON decoding error: {str(e)}"}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}




# Define the /webhook route
@app.route('/Find', methods=['POST'])
def Find():
    try:
        # Get phone number from request JSON
        req_data = request.get_json()
        print(req_data)
        req_data = req_data['sessionInfo']['parameters']
        phone_number = req_data.get('phone_number')  # Change the key based on your webhook payload

        if phone_number:
            # Call get_client_by_phone function to get client info by phone number from Jobber
            try:
                client_info = get_client_by_phone(phone_number)

            
        
                if client_info and client_info[0].get('id') and client_info[0].get('name'):
                    # Extracting the client ID and name
                    client_id = client_info[0].get('id')
                    client_name = client_info[0].get('name')
                    
                    # Setting session parameters in the response
                    return jsonify({
                        'sessionInfo': {
                            'parameters': {
                                'clientExists': True,   # Setting 'clientExists' to True
                                'clientId': client_id,
                                'clientName': client_name
                            }
                        }
                    })
            except:
                # Client ID or name not found, return response accordingly
                return jsonify({
                    'sessionInfo': {
                        'parameters': {
                            'clientExists': False  # Setting 'clientExists' to False
                        }
                    }
                })
        
            # print(client_info)
            # return jsonify({
            #     'status': 'success',
            #     'client_info': client_info
            # }), 200
        else:
            print("No phone_number provided in the request")
            return jsonify({
                'status': 'error',
                'message': 'No phone_number provided in the request.'
            }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/create_request', methods=['POST'])
def create_request():
    try:
        req_data = request.get_json()
        print(req_data)

        service = req_data['sessionInfo']['parameters'].get('service')
        treecuttingpermit = None  # Initialize treecuttingpermit with None or a default value
        
        if service == 'Tree Cutting':
            treecuttingpermit = req_data['sessionInfo']['parameters'].get('treecuttingpermit')
        
        work_location = req_data['sessionInfo']['parameters'].get('work_location')
        work_plan = req_data['sessionInfo']['parameters'].get('work_plan')
        assessment = req_data['sessionInfo']['parameters'].get('assessment')
        clientId = req_data['sessionInfo']['parameters'].get('clientId')
        
        # Call your function with all the necessary parameters
        client_info = create_request_including_custom_form(clientId, assessment, work_plan, work_location, treecuttingpermit, service)
        
        print(client_info)
        return jsonify({
            'status': 'success',
            'client_info': client_info
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



@app.route('/create', methods=['POST'])
def create():
    try:
        # Get phone number and other details from request JSON
        req_data = request.get_json()
        print(req_data)
        
        # Extract necessary parameters from the request
        business_name = req_data['sessionInfo']['parameters'].get('business-name')
        city = req_data['sessionInfo']['parameters'].get('city')
        country = req_data['sessionInfo']['parameters'].get('country')
        email = req_data['sessionInfo']['parameters'].get('email')
        first_name = req_data['sessionInfo']['parameters'].get('first-name')
        last_name = req_data['sessionInfo']['parameters'].get('last-name')
        phone_number = req_data['sessionInfo']['parameters'].get('phone_number')
        postalcode = req_data['sessionInfo']['parameters'].get('postalcode')
        province = req_data['sessionInfo']['parameters'].get('province')
        street = req_data['sessionInfo']['parameters'].get('street_address')

        # Call the create_client function to create the client in Jobber
        client_info = create_client(first_name, last_name, phone_number, business_name, email, street, city, province, country, postalcode)
        print(client_info)
        
        # If client creation was successful, set session parameters
        if client_info['status'] == 'success':
            client_id = client_info['client_info']['id']
            client_name = f"{client_info['client_info']['firstName']} {client_info['client_info']['lastName']}"
            
            # Update session parameters
            session_parameters = {
                "clientId": client_id,
                "clientName": client_name,
                "clientExists": True
            }

            return jsonify({
                'status': 'success',
                'client_info': client_info['client_info'],
                'sessionInfo': {
                    'parameters': session_parameters
                }
            }), 200
        
        # Handle error in client creation
        else:
            return jsonify({
                'status': 'error',
                'message': client_info['message']
            }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Run Flask app
    app.run(debug=True)
