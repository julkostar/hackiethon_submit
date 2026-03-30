"""How to run"""


# Windows:
# Open up powershell or cmd prompt and type to open the venv:
python -m venv venv 

# Activate:
.\venv\Scripts\activate

# If there is an error your system may block the venv
# Run this prior to activation to amend:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Mac:
python3 -m venv venv

source venv/bin/activate



# For both:
# Install all libraries in requirements.txt
pip install -r requirements.txt

# Create .env file and add GROQ_KEY (Must provide your own)
GROQ_KEY = #Insert your GROQ key from https://console.groq.com/keys

# Running the game from terminal
python main.py run



