# WaveLink

This application allows you to control and play music from Spotify using your phone.


**Note :** This project works correctly only on Windows. You may encounter errors on other operating systems.

**Note :** The installation and execution steps below apply to Windows 10 or 11.

# Installition
Requirements :
  - Windows 10/11
  - Python 3.10+
  - Spotify Developer App Credentials

```batch
python install -r reqs.txt
```

After installing the modules:
- Create an application at https://developer.spotify.com/dashboard.
- Enter `http://localhost:8888/callback` as the Redirect URI for the application you created and select the **Web API** section.
- Enter the application's `Client ID` and `Client Secret` into the `config.json` file.


# Running
```batch
python main.py
```

# Usage
After starting the server on your computer, open `http://{PC_IP}:5000` on your phone.
You can start using it after switching your phone to landscape mode.
