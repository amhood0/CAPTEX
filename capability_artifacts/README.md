# Semester demonstration artifacts

These bundled artifacts appear automatically in the capability artifact picker.
All use `python3 run.py` as their execution command and require only Python's
standard library. Run automated tests in the managed Ubuntu environment.

## Text Summary: two versions, one test plan

Create a capability named **Text Summary** with version **1.0**, selecting
`text-summary-v1`. Add version **2.0-broken** to the same capability, selecting
`text-summary-v2-broken`. Set `python3 run.py` for both versions.

Both read the same bundled `input.txt`, print a summary, and write `summary.txt`
in the execution working directory. The input contains three lines and 12 words.
Version 2 deliberately adds one to the word count, reporting 13 words.

Create one test plan for Text Summary with these enabled cases, in this order
(a 10-second timeout per case is sufficient):

| Case | Test type | Expected result | Version 1 | Version 2 |
| --- | --- | --- | --- | --- |
| Successful execution | `exit_code` | `0` | PASS | PASS |
| Correct word count | `stdout_contains` | `Words: 12` | PASS | FAIL |
| Summary file created | `file_exists` | `summary.txt` | PASS | PASS |

Run the plan against version 1, then against version 2. The overall outcomes
should be PASS and FAIL respectively. Open each run's results and output to
show the changed word count, and use run history to review both versions.
This demonstrates a regression through recorded results; it does not require
an automatic version-comparison report.

The runner executes the command separately for each test case. These examples
overwrite their output on each execution, so repeated runs are deterministic.
The file-existence check proves the file was created, not that its contents
are correct; the stdout check catches this particular defect.

## Message-only simulation

Create a separate capability named **Simulated malware: message-only**, version
**1.0**, selecting `message-only-simulation` and command `python3 run.py`.
Create a plan with these enabled cases and 10-second timeouts:

| Case | Test type | Expected result |
| --- | --- | --- |
| Successful execution | `exit_code` | `0` |
| Expected message | `stdout_contains` | `youve been hacked` |

Both cases should PASS. This script only prints the message and exits; it does
not modify files, access the network, or persist. Present it as a harmless
malware-themed simulation. PASS means the expected behavior was observed,
not that CAPTEX detected malware or certified the sample as safe.

The existing `phase6-demo` remains available as a basic automation smoke test.
