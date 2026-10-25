from app.services.discord_client import register_guild_commands

COMMANDS = [
    {
        "name": "approve",
        "description": "Approve a proposed affiliate program",
        "options": [
            {
                "name": "program",
                "description": "Program UUID or exact name",
                "type": 3,
                "required": True,
            }
        ],
    },
    {
        "name": "reject",
        "description": "Reject a proposed affiliate program",
        "options": [
            {
                "name": "program",
                "description": "Program UUID or exact name",
                "type": 3,
                "required": True,
            }
        ],
    },
]


def main() -> None:
    register_guild_commands(COMMANDS)


if __name__ == "__main__":
    main()
