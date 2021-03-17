
# porkbun-cli
A simple command line interface for managing your porkbun domains.
 - Create/Delete domain records
 - Edit existing domain records
 - Update record content:
	 - By command line
	 - By current external IP address
	 - Periodically, to pick changes in external address (useful if you have a dynamic IP)

## Dependencies
- docopt (`python3 -m pip install docopt`)

That's it!

## Usage:
### Setup:
Before using this tool, you will need to generate API keys for your porkbun account and enable API access for any domains that you want to manage with this tool. You can do this from your porkbun dashboard. The tool expects to see two files in it's working directory:

`api-key`
`secret-api-key`

Which should contain your api and secret keys respectively. Remember to set appropriate file permissions for your secret key!

### Command line:
The first thing you should probably do is ping the porkbun API to check that your API keys are set up correctly:

`python3 porkbun-cli ping`

The tool also has comprehensive help output:

`python3 porkbun-cli -h`

If you are unfamiliar with command line interfaces like this one and find the help message confusing, then here is a brief summary:
- `<>` Indicates an input field
- `[]` Indicates an optional argument
- `(A|B)` Indicates that you may specify A or B, but not both
- `-` or `--` Indicates an option

If you are a programmer and want to learn how to create beautiful command line interfaces like this one, then [look no further](http://docopt.org/)!

## Periodic updates:
This tool can be used to create a dynamic updater that will update the content of a record periodically to keep track with your external IP address. This is especially useful if you want your record to point at a residential connection with a dynamic IP.

For example, the following command will check your external IP address every 5 seconds and update the specified record if the IP changes:

`python3 porkbun-cli record update <domain> <record-id> --delay=5`

The record id can be obtained by listing the records associated with your domain:

`python3 porkbun-cli record list <domain>`

### Installation as a systemd unit:
TODO
