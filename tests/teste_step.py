import chainlit as cl

@cl.on_message
async def main():
    async with cl.Step(name="Test") as step:
        # Step is sent as soon as the context manager is entered
        step.output = "hello world"

    # Step is updated when the context manager is exited