import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
import json
import os

class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🆘 Support", style=discord.ButtonStyle.blurple, custom_id="ticket_support")
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "support")

    @discord.ui.button(label="🐛 Bug Report", style=discord.ButtonStyle.danger, custom_id="ticket_bug")
    async def bug_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "bug")

    @discord.ui.button(label="💡 Suggestion", style=discord.ButtonStyle.success, custom_id="ticket_suggestion")
    async def suggestion_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "suggestion")

    @discord.ui.button(label="📝 Application", style=discord.ButtonStyle.secondary, custom_id="ticket_application")
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "application")

    async def create_ticket(self, interaction: discord.Interaction, category: str):
        guild = interaction.guild
        user = interaction.user

        ticket_number = await self.get_next_ticket_number()
        channel_name = f"ticket-{category}-{ticket_number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        support_role = guild.get_role(os.getenv('SUPPORT_ROLE_ID', 0))
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        category_obj = discord.utils.get(guild.categories, name="Tickets")
        if not category_obj:
            category_obj = await guild.create_category("Tickets")

        ticket_channel = await category_obj.create_text_channel(channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title=f"Ticket #{ticket_number} - {category.upper()}",
            description=f"Thank you {user.mention} for creating a ticket!\n\nA staff member will be with you shortly.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="Use /close to close this ticket")

        close_view = CloseTicketView(self.bot)
        await ticket_channel.send(embed=embed, view=close_view)

        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

        log_channel = guild.get_channel(int(os.getenv('LOG_CHANNEL_ID', 0)))
        if log_channel:
            log_embed = discord.Embed(
                title="📋 Ticket Created",
                description=f"**User:** {user.mention}\n**Category:** {category}\n**Channel:** {ticket_channel.mention}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            await log_channel.send(embed=log_embed)

    async def get_next_ticket_number(self):
        if not os.path.exists('tickets_data'):
            os.makedirs('tickets_data')
        
        counter_file = 'tickets_data/counter.json'
        if os.path.exists(counter_file):
            with open(counter_file, 'r') as f:
                data = json.load(f)
                next_num = data.get('next', 1)
        else:
            next_num = 1

        with open(counter_file, 'w') as f:
            json.dump({'next': next_num + 1}, f)

        return next_num


class CloseTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"Closed by {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )

        log_channel = guild.get_channel(int(os.getenv('LOG_CHANNEL_ID', 0)))
        if log_channel:
            await log_channel.send(embed=embed)

        await interaction.response.defer()
        await channel.delete()


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="panel", description="Create a ticket panel (Admin only)")
    @commands.has_permissions(administrator=True)
    async def panel(self, ctx):
        embed = discord.Embed(
            title="📋 Support Ticket System",
            description="Click a button below to create a ticket for your issue.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="🆘 Support", value="General support questions", inline=False)
        embed.add_field(name="🐛 Bug Report", value="Report a bug", inline=False)
        embed.add_field(name="💡 Suggestion", value="Share a suggestion", inline=False)
        embed.add_field(name="📝 Application", value="Submit an application", inline=False)

        await ctx.respond(embed=embed, view=TicketView(self.bot))

    @commands.slash_command(name="claim", description="Claim a ticket")
    async def claim(self, ctx):
        if "ticket" not in ctx.channel.name:
            await ctx.respond("This is not a ticket channel!", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Ticket Claimed",
            description=f"This ticket has been claimed by {ctx.user.mention}",
            color=discord.Color.green()
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="close", description="Close this ticket")
    async def close(self, ctx):
        if "ticket" not in ctx.channel.name:
            await ctx.respond("This is not a ticket channel!", ephemeral=True)
            return

        embed = discord.Embed(
            title="❓ Close Reason",
            description="Please provide a reason for closing this ticket.",
            color=discord.Color.orange()
        )
        
        await ctx.respond("Ticket will be closed in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await ctx.channel.delete()


def setup(bot):
    bot.add_cog(Ticket(bot))