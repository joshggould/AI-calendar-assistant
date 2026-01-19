import argparse
import subprocess
import os
import calassist


parser = argparse.ArgumentParser(description="AI Calendar Assistant")
parser.add_argument('text', nargs='+', help="Full sentence describing the event")
parser.add_argument("-i",'--input', choices=["interactive", "cli"], default="cli",help="Choose input mode: interactive or cli")
args = parser.parse_args()


if args.input == "interactive":
    user_input = input("Enter your event: ")
else:
    user_input = " ".join(args.text)

print("Input received:", user_input)

#want to be able to add and delete events
#modify events change dates and times
#share events? 