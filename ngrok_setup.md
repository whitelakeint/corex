 Option 1: Quick Test - Use ngrok (Fastest)

  Install and run ngrok to create an HTTPS tunnel:

  # On the remote server
  cd /home/jnpwladmin

  # Download ngrok
  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
  tar -xvzf ngrok-v3-stable-linux-amd64.tgz

  # Sign up at https://dashboard.ngrok.com to get auth token
  ./ngrok config add-authtoken YOUR_AUTH_TOKEN

  # Create HTTPS tunnel to your app
  ./ngrok http 8001

  This gives you a secure HTTPS URL like https://abc123.ngrok.io that you can use to access your app with camera/microphone
  working.


● Run ngrok in the background with nohup:

  # Run ngrok in background
  nohup ./ngrok http 8001 > ngrok.log 2>&1 &

  # Get the public URL
  curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*ngrok[^"]*'

pkill ngrok

  To check the current ngrok URL anytime:

  curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*ngrok[^"]*'
