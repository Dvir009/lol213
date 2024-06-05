import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from datetime import datetime, timedelta
import html
import io  # Add this import

# Role ID that needs access to ticket channels
ROLE_ID = 1247516699352104980

# Log channel ID
LOG_CHANNEL_ID = 1247602481106653275  # Replace with your log channel ID

# Initialize the bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Event to respond to "hi"
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content == 'hi':
        await message.channel.send('hi')
    await bot.process_commands(message)

# Command to close a ticket
@bot.command(name='close')
async def close_ticket(ctx):
    channel = ctx.channel
    if "ticket-" in channel.name:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        # Collect messages from the ticket channel
        messages = [message async for message in channel.history(limit=None)]
        messages.reverse()  # To maintain the order of messages

        # Format messages into HTML
        html_content = "<html><body><h2>Ticket Log</h2><ul>"
        for message in messages:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = html.escape(message.author.display_name)
            content = html.escape(message.content)
            html_content += f"<li><b>{timestamp} - {author}:</b> {content}</li>"
        html_content += "</ul></body></html>"

        # Create an in-memory file for the HTML content
        html_file = discord.File(fp=io.BytesIO(html_content.encode()), filename=f"{channel.name}.html")

        # Send the HTML content to the log channel as a file
        await log_channel.send(embed=discord.Embed(
            title="Ticket Closed",
            description=f'Ticket channel {channel.name} closed by {ctx.author.mention}.',
            color=discord.Color.red()
        ), file=html_file)

        await ctx.send('Closing this ticket channel...')
        await channel.delete()
    else:
        await ctx.send('This command can only be used in ticket channels.')

# Command to rename a ticket
@bot.command(name='rename_ticket')
async def rename_ticket(ctx, new_name: str):
    channel = ctx.channel
    if "ticket-" in channel.name:
        old_name = channel.name
        await channel.edit(name=new_name)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(embed=discord.Embed(
            title="Ticket Renamed",
            description=f'Ticket channel {old_name} renamed to {new_name} by {ctx.author.mention}.',
            color=discord.Color.blue()
        ))
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
    else:
        await ctx.send('This command can only be used in ticket channels.')

# Command to send the ticket button
@bot.command(name='send_ticket_button')
async def send_ticket_button(ctx):
    button = Button(label='Open Ticket', style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        options = [
            discord.SelectOption(label="תרומה", value="donation", emoji="💰", description="קבלת מוצרים שקנית"),
            discord.SelectOption(label="תלונה על צוות", value="complaint", emoji="🔔", description="להגיש תלונה על חבר צוות"),
            discord.SelectOption(label="עירעור על באן", value="appeal", emoji="⛔", description="להגיש עירעור על באן"),
            discord.SelectOption(label="שאלה", value="question", emoji="❓", description="להגיש שאלה"),
            discord.SelectOption(label="החזרת דברים", value="return", emoji="♻", description="להגיש בקשה להחזרת דברים"),
            discord.SelectOption(label="הכנסת פד", value="add_pad", emoji="👤", description="להגיש בקשה להוספת פד למשחק"),
            discord.SelectOption(label="תלונה על שחקן", value="player_complaint", emoji="⚠", description="להגיש תלונה על שחקן")
        ]
        select = Select(options=options, placeholder="בחר אפשרות")
        view = View()
        view.add_item(select)

        async def select_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeout

            selected_option = interaction.data['values'][0]
            category_name = selected_option.lower()

            author = interaction.user
            channel_name = f'ticket-{author.name}'

            # Check if a channel with this name already exists
            existing_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
            if existing_channel is not None:
                await interaction.followup.send(f'You already have a ticket channel: {existing_channel.mention}', ephemeral=True)
                return

            # Find the role by ID
            role = ctx.guild.get_role(ROLE_ID)

            # Create a new channel and set permissions
            category = discord.utils.get(ctx.guild.categories, name=category_name)
            if not category:
                category = await ctx.guild.create_category(category_name)

            channel = await ctx.guild.create_text_channel(channel_name, category=category)
            await channel.set_permissions(author, read_messages=True, send_messages=True)
            await channel.set_permissions(role, read_messages=True, send_messages=True)
            await channel.set_permissions(ctx.guild.default_role, read_messages=False)

            # Get the current time for the ticket creation in Israel time
            israel_time = datetime.utcnow() + timedelta(hours=3)
            timestamp = israel_time.strftime("%I:%M %p")

            # Embed for ticket creation
            embed = discord.Embed(
                title="Ticket Opened",
                description=f"Hey {author.mention}, welcome to name | Allowlist Roleplay Ticket system\nYou opened a ticket with issue regarding {selected_option.capitalize()}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Today at {timestamp} ")

            staff_button = Button(label="Staff Options", style=discord.ButtonStyle.blurple)
            claim_button = Button(label="Claim", style=discord.ButtonStyle.green)
            close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

            async def staff_button_callback(interaction: discord.Interaction):
                rename_button = Button(label="Rename Ticket", style=discord.ButtonStyle.blurple)
                add_member_button = Button(label="Add Member", style=discord.ButtonStyle.green)

                async def rename_button_callback(interaction: discord.Interaction):
                    await interaction.response.send_message('Please enter the new ticket name:', ephemeral=True)
                    def check(m):
                        return m.author == interaction.user and m.channel == interaction.channel
                    new_name_msg = await bot.wait_for('message', check=check)
                    new_name = new_name_msg.content
                    old_name = channel.name
                    await channel.edit(name=new_name)
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    await log_channel.send(embed=discord.Embed(
                        title="Ticket Renamed",
                        description=f'Ticket channel {old_name} renamed to {new_name} by {interaction.user.mention}.',
                        color=discord.Color.blue()
                    ))
                    await interaction.followup.send(f'Ticket renamed to {new_name}', ephemeral=True)

                async def add_member_button_callback(interaction: discord.Interaction):
                    await interaction.response.send_message('Please enter the ID of the member to add:', ephemeral=True)
                    def check(m):
                        return m.author == interaction.user and m.channel == interaction.channel
                    member_id_msg = await bot.wait_for('message', check=check)
                    member_id = int(member_id_msg.content)
                    member = ctx.guild.get_member(member_id)
                    if member:
                        await channel.set_permissions(member, read_messages=True, send_messages=True)
                        await interaction.followup.send(f'Member {member.mention} added to the ticket.', ephemeral=True)
                        log_channel = bot.get_channel(LOG_CHANNEL_ID)
                        await log_channel.send(embed=discord.Embed(
                            title="Member Added to Ticket",
                            description=f'Member {member.mention} added to ticket channel {channel.name} by {interaction.user.mention}.',
                            color=discord.Color.green()
                        ))
                    else:
                        await interaction.followup.send('Member not found.', ephemeral=True)

                rename_button.callback = rename_button_callback
                add_member_button.callback = add_member_button_callback

                options_view = View()
                options_view.add_item(rename_button)
                options_view.add_item(add_member_button)

                await interaction.response.send_message("Staff Options:", view=options_view, ephemeral=True)

            async def claim_button_callback(interaction: discord.Interaction):
                await channel.send(f"{author.mention} this ticket has been claimed by {interaction.user.mention}.")
                button_view.remove_item(claim_button)
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                await log_channel.send(embed=discord.Embed(
                    title="Ticket Claimed",
                    description=f'Ticket channel {channel.name} claimed by {interaction.user.mention}.',
                    color=discord.Color.orange()
                ))
                await interaction.response.edit_message(view=button_view)

            async def close_button_callback(interaction: discord.Interaction):
                confirmation_view = View()
                confirm_button = Button(label="Close", style=discord.ButtonStyle.red)

                async def confirm_callback(interaction: discord.Interaction):
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)

                    # Collect messages from the ticket channel
                    messages = [message async for message in channel.history(limit=None)]
                    messages.reverse()  # To maintain the order of messages

                    # Format messages into HTML
                    html_content = "<html><body><h2>Ticket Log</h2><ul>"
                    for message in messages:
                        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        author = html.escape(message.author.display_name)
                        content = html.escape(message.content)
                        html_content += f"<li><b>{timestamp} - {author}:</b> {content}</li>"
                    html_content += "</ul></body></html>"

                    # Create an in-memory file for the HTML content
                    html_file = discord.File(fp=io.BytesIO(html_content.encode()), filename=f"{channel.name}.html")

                    # Send the HTML content to the log channel as a file
                    await log_channel.send(embed=discord.Embed(
                        title="Ticket Closed",
                        description=f'Ticket channel {channel.name} closed by {interaction.user.mention}.',
                        color=discord.Color.red()
                    ), file=html_file)

                    await channel.delete()

                confirm_button.callback = confirm_callback
                confirmation_view.add_item(confirm_button)

                await interaction.response.send_message("Are you sure you would like to close this ticket?", view=confirmation_view, ephemeral=True)

            staff_button.callback = staff_button_callback
            claim_button.callback = claim_button_callback
            close_button.callback = close_button_callback

            button_view = View()
            button_view.add_item(staff_button)
            button_view.add_item(claim_button)
            button_view.add_item(close_button)

            await channel.send(f"{author.mention} {role.mention}", embed=embed, view=button_view)

            await interaction.followup.send(f'Ticket channel created: {channel.mention}', ephemeral=True)

        select.callback = select_callback
        await interaction.response.send_message("Select a category for the ticket:", view=view, ephemeral=True)

    button.callback = button_callback
    view = View()
    view.add_item(button)

    embed = discord.Embed(title="Ticket support", description="Click on the button below to open a ticket!", color=discord.Color.blue())
    embed.set_thumbnail(url="https://user-images.githubusercontent.com/14011726/94132137-7d4fc100-fe7c-11ea-8512-69f90cb65e48.gif")
    await ctx.send(embed=embed, view=view)

# Run the bot
bot.run(TOKEN)
