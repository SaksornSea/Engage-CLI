import subprocess
import sys
import os
import importlib.util


print("Welcome to the Engage CLI Setup Wizard!")
print("By Sea :)")

def check_and_install_package(package_name, import_name):
    """Checks if a package is installed and installs it if not."""
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        print(f"Package '{import_name}' not found. Attempting to install '{package_name}'...")
        pip_command = [sys.executable, "-m", "pip", "install", package_name]

        # Check if running in a virtual environment
        # sys.prefix == sys.base_prefix indicates not in a virtual environment
        if sys.prefix == sys.base_prefix:
            # Not in a virtual environment, add --break-system-packages as requested
            print("Warning: Not in a virtual environment. Using --break-system-packages.")
            pip_command.append("--break-system-packages")
        else:
            print("Detected virtual environment. Installing without --break-system-packages.")

        try:
            subprocess.check_call(pip_command)
            print(f"Successfully installed '{package_name}'.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing '{package_name}': {e}")
            print("Please ensure pip is installed and accessible, or try running in a virtual environment.")
            sys.exit(1)
    else:
        print(f"Package '{import_name}' is already installed.")

print("\n" + "-" * 50)
print("1. Installing dependencies")
print("-" * 50 + "\n")

check_and_install_package("requests", "requests")
check_and_install_package("beautifulsoup4", "bs4")

print("\n" + "-" * 50)
print("2. Create engage.config")
print("-" * 50 + "\n")


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
