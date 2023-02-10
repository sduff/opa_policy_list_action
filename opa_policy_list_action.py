#!/usr/bin/python

# Validate rego policies from policies.hcl file ala Terraform Cloud
#
# Simon Duff
# https://linkedin.com/in/sduff/

import re, sys, json, argparse, subprocess

# Basic config options
parser = argparse.ArgumentParser(
    prog = 'opa_policy_list_action',
    description = 'Apply every policy in a policies.hcl file and summarise the results')
parser.add_argument('--ascii', action='store_true', help='Use ASCII only, no unicode characters')
parser.add_argument('--timeout', type=int, default=30, help='how to long to allow each policy to run')
parser.add_argument('--policies_file', default='./policies.hcl', help='file containing policy list')
parser.add_argument('--input_file', default='./tfplan.json', help='input file to check policies against')
parser.add_argument('--opa_binary', default='opa', help='opa binary location')
parser.add_argument('--show_all', action='store_true', help='show all policy results, not just failures')
parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
args = parser.parse_args()


# Run the actual policy and return the results
def run_policy(policy_file, input_file, query, timeout=args.timeout):
    result = {"return_code": 0}

    # determine the proper filename

    try:
        r = subprocess.run(
            [
                args.opa_binary, "eval",
                "--data", policy_file,
                "--input", input_file,
                "--format", "raw",
                "--fail",
                query
            ],
            timeout=timeout, capture_output=True, text=True)

        result["stdout"] = r.stdout
        result["stderr"] = r.stderr
        result["original_return_code"] = r.returncode

        if r.returncode == 0:
            msg = re.findall('"[^"]+"', r.stdout, flags=re.M)
            result["msg"] = msg

            if len(msg) > 0:
                result["return_code"] = 1
        else:
            if r.stdout:
                result["msg"] = ["opa failure: %s"%(r.stdout.strip())]
            elif r.stderr:
                result["msg"] = ["opa failure: %s"%(r.stderr.strip())]
            else:
                result["msg"] = ["opa failure: Unknown"]
            result["return_code"] = 1

    except FileNotFoundError as exc:
        result["msg"] = [f"opa failure: %s"%(exc)]
        result["return_code"] = 255

    except subprocess.TimeoutExpired as exc:
        result["msg"] = [f"opa failure: policy took too long to run"]
        result["return_code"] = 255

    return result

# Parse the policies.hcl file
return_code = 0
try:
    with open(args.policies_file, "r") as pf:
        data = pf.read()

        # strip comments
        data = re.sub("#.*\n", "", data, flags=re.M)

        # dirty tokenizer
        data = re.findall('policy\W*"[^"]+"\W*{[^}]*}', data, flags=re.M)

        # run each policy
        return_code = 0
        msgs = []
        for d in data:
            name = (re.search('policy\W*"([^"]+)"', d)).group(1)
            query = (re.search('query\W*=\W*"([^"]+)"', d)).group(1)
            level = (re.search('enforcement_level\W*=\W*"([^"]+)"', d)).group(1).lower()

            result = run_policy(name, args.input_file, query)

            if result["return_code"] != 0 or args.show_all:
                if args.ascii:
                    if result["return_code"] == 0:
                        icon = "[ OK ]"
                    elif result["return_code"] == 1 and level == "advisory":
                        icon = "[INFO]"
                        if return_code == 0:
                            return_code = 1
                    else: # mandatory and failure
                        icon = "[FAIL]"
                        return_code = 2
                else:
                    #         Advisory Mandatory
                    # Success    ✅       ✅
                    # Failure    ⚠️        ❌
                    if result["return_code"] == 0:
                        icon = "✅"
                    elif result["return_code"] == 1 and level == "advisory":
                        icon = "⚠️ "
                        if return_code == 0:
                            return_code = 1
                    else: # mandatory and failure
                        icon = "❌"
                        return_code = 2

                print (f"{icon} {name}")
                for m in result["msg"]:
                    print("\t",m)


except FileNotFoundError as e:
    print(f"FATAL: Unable to parse policy file, looked for {args.policies_file}")
    return_code = 1

# return code
sys.exit(return_code)
