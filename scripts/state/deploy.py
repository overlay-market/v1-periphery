import click
from brownie import OverlayV1State, accounts, network


# overlay market factory address
# TODO: change
FACTORY = "0x8cCD181113c7Ae40f31D5e8178a98A1A60B55c4C"


def main():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt(
        "Account", type=click.Choice(accounts.load())))

    # deploy market state contract
    state = OverlayV1State.deploy(FACTORY, {"from": dev}, publish_source=True)
    click.echo(f"State deployed [{state.address}]")
