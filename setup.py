import subprocess
import sys


download_url = "https://sea.navynui.cc/tools/engage/assets/engage.txt"

print("Welcome to the Engage CLI Setup Wizard!")
print("By Sea :)")

print("\n" + "-" * 50)
print("1. Install Librares")
print("2. Download engage.py")
print("3. Create engage.config")
print("-" * 50 + "\n")


def install_package(package_name):
    """
    Installs a specified Python package using pip via subprocess.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--break-system-packages"])
        print(f"Successfully installed {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package_name}: {e}")

def download_file(url, filename):
    """
    Downloads a file from a URL using the requests library.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, allow_redirects=True)
        # Check if the request was successful (status code 200)
        response.raise_for_status()

        # Open a file in binary write mode ('wb') and write the content
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"File '{filename}' downloaded successfully.")

    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        exit(1)


# install packages
install_package("requests")
install_package("bs4")
try:
    import requests
    print("\nLibrares downloaded and imported successfully!\n")
except ImportError:
    print("\nERROR: Librares could not be imported\n")
    exit(0)


# Download file
print("Downloading engage.py...")
save_as_filename = 'engage.py'
download_file(download_url, save_as_filename)

print("\nTime to create the config file!")
print("\n")
print("You'll now need to get the subdomain of your School's Engage URL.")
print("Example: https://#######.engagehosted.com")
print("                    ^")
print("                    |")
print("             This thing here")
subdomain = input("Enter your subdomain here: ")
print("\n")


print("Now we need your engage account credentials.")
username = input("Enter your username here: ")
password = input("Enter your password here: ")
print("As an extra touch, you can name your account! You can name it anything you want. (Example: My Account)")
name = input("Enter your account name here: ")
print("\n")

with open('engage.config', 'w') as f:
    f.write(f'subdomain: {subdomain}\n')
    f.write(f'acc0:\n')
    f.write(f'name: {name}\n')
    f.write(f'username: {username}\n')
    f.write(f'password: {password}\n')

print("Setup is now complete!")
print("\n")
print("You can now run Engage CLI by typing 'python engage.py' in your terminal.")
print("Make sure NOT to rename or delete the engage.config file.")
print("You can now delete this setup.py file.")
print("Have fun using Engage CLI!")
