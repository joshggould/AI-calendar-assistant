import argparse


parser = argparse.ArgumentParser(description="AI Calendar Assistant")
parser.add_argument('text', nargs='+', help="Full sentence describing the event")
parser.add_argument("--i",'--input', choices=["interactive", "cli"], default="cli",help="Choose input mode: interactive or cli")
args = parser.parse_args()

if args.input == "interactive":
    user_input = input("Enter your event: ")
else:
    # grab CLI input sentence
    parser.add_argument("text", nargs='+', help="Event description for CLI mode")
    cli_args = parser.parse_args()
    user_input = " ".join(cli_args.text)

print("Input received:", user_input)

#want to be able to add and delete events
#modify events change dates and times
#share events? 