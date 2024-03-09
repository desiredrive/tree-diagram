from dataclasses import dataclass
import radkit_client


from radkit_client.sync import (
    # For the creation of the context.
    create_context,
    # Cloud-based login methods.
    certificate_login,
    access_token_login,
    sso_login,
    # Direct login method.
    direct_login,
)

def main(service: radkit_client.Service):
    """
    :param service: radkit_client.Service object
    """
    
def radkit_login(email: str, domain: str, serial: str):
    # Connect to the given service, using SSO login.
    client = certificate_login(identity=email, domain=domain)
    service = client.service(serial).wait()
    return service

def get_any_single_output(hostname,command: str,service):
    try:
        device_inventory = service.inventory[hostname]
        commands = device_inventory.exec([command]).wait()
        try:
            output = commands.result["{}".format(command)].data
        except:
            return None
    except ValueError:
        print ("Error when getting the following command: {}".format(commands))
    return output

