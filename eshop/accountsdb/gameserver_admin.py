from django.contrib import admin
from .models import GameServer

try:
    admin.site.unregister(GameServer)
except admin.sites.NotRegistered:
    pass

@admin.register(GameServer)
class GameServerAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "name", "host", "port", "device", "is_public", "maintenance_mode")
    list_editable = ("name", "host", "port", "is_public", "maintenance_mode")
    list_display_links = ("id", "client_id")
    search_fields = ("client_id", "name", "host", "device")
    list_filter = ("is_public", "maintenance_mode", "device")
    fields = ("client_id", "name", "host", "port", "aes_key", "device", "is_public", "maintenance_mode", "created_at")
    readonly_fields = ("created_at",)
    save_on_top = True
