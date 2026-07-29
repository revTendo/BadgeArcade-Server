from django.contrib import admin
from .models import region

@admin.register(region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "initial")
    search_fields = ("name", "initial")
    list_per_page = 50
    save_on_top = True
