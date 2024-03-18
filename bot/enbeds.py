import nextcord


class SimpleEmbed:
    @staticmethod
    def success(text):
        return nextcord.Embed(title='', description='✅ ' + text, color=0x2B2D31)

    @staticmethod
    def error(text):
        return nextcord.Embed(title='', description='❌ ' + text, color=0x2B2D31)
