from dotenv import load_dotenv
import anthropic
import discord
import os

# Load environment variables from .env file
load_dotenv()
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DISCORD_TOKEN = os.getenv('TOKEN')

# Initialize the Anthropic client
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def call_claude(question):
    message = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Respond like a pirate to the following question: {question}",
            },
        ]
    )
    response = message.content[0].text
    print(response)
    return response


# Set up discord
intents = discord.Intents.default()
intents.message_content = True  
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    if message.content.startswith('$question'):
        print(f"Message: {message.content}")
        message_content = message.content.split("$question")[1]
        print(f"Question: {message_content}")
        response = call_claude(message_content)
        print(f"Assistant: {response}")
        print("---")
        await message.channel.send(response)

client.run(DISCORD_TOKEN)
