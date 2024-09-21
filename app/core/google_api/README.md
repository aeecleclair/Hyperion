# Google API usage in Hyperion

Hyperion can use Google API to run App Script and upload files to Google Drive.

## Configuration

You need to configure a client id and secret in the dotenv:

```yml
GOOGLE_API_CLIENT_ID
GOOGLE_API_CLIENT_SECRET
```

1. Go to https://console.cloud.google.com/projectcreate and create a new project
2. Select the project and open [API and Services](https://console.cloud.google.com/apis/dashboard)
3. Select "Library" and add the following libraries:
   a. Google Drive API
   b. Google Sheets API
   c. Apps Script API
4. Go to [Credentials](https://console.cloud.google.com/apis/credentials). Select "Configure Consent Screen"
   a. User Type : Internal
5. Go to [Credentials](https://console.cloud.google.com/apis/credentials). Select "Create credentials" then:
   a. OAuth client id
   b. Web Application
   c. Redirect uri: "https://<yourdomain>/google-api/oauth2callback"
