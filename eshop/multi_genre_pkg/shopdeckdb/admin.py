from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.site_header = "Shopdeck Administration"
admin.site.site_title = "Shopdeck Admin"
admin.site.index_title = "Manage your shop"

@admin.register(Client3DS)
class Client3DSAdmin(admin.ModelAdmin):
    list_display = ("id", "consoleid", "region", "country", "language", "balance", "is_terminated")
    list_filter = ("region", "country", "language", "is_terminated")
    search_fields = ("consoleid", "devicetoken", "uniquekey", "devicecert_consoleid")
    list_per_page = 50

@admin.register(User)
class ShopUserAdmin(UserAdmin):
    list_display = ("username", "email", "linked_ds", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    autocomplete_fields = ("linked_ds",)
    fieldsets = UserAdmin.fieldsets + (("3DS link", {"fields": ("linked_ds",)}),)

@admin.register(publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("id", "publisher_name")
    search_fields = ("publisher_name",)

@admin.register(genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "index", "order", "standard", "new")
    list_filter = ("standard", "new")
    search_fields = ("name",)

@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tid", "publisher", "platform", "price", "version", "public", "new")
    list_filter = ("public", "new", "platform", "genre", "in_app_purchase", "is_not_downloadable")
    search_fields = ("name", "tid", "product_code", "desc")
    autocomplete_fields = ("publisher", "category", "platform", "demo")
    filter_horizontal = ("genre",)
    list_editable = ("price", "public")
    list_per_page = 50

@admin.register(item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "itemcode", "title", "content_index", "price", "limit")
    list_filter = ("title__platform",)
    search_fields = ("name", "itemcode", "title__name", "title__tid", "content_index")
    autocomplete_fields = ("title",)
    list_per_page = 50

class dlcContentSetAttributeInline(admin.TabularInline):
    model = dlcContentSetAttribute
    extra = 1

class dlcContentSetInline(admin.StackedInline):
    model = dlcContentSet
    extra = 1
    show_change_link = True

@admin.register(dlcContentTitle)
class DlcContentTitleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tid", "paginated", "page_limit")
    list_filter = ("paginated",)
    search_fields = ("tid", "name")
    inlines = (dlcContentSetInline,)

@admin.register(dlcContentSet)
class DlcContentSetAdmin(admin.ModelAdmin):
    list_display = ("id", "dlc", "order", "content_indexes", "itemcode", "price", "currency")
    list_filter = ("dlc", "currency")
    search_fields = ("dlc__tid", "itemcode", "content_indexes")
    autocomplete_fields = ("dlc",)
    inlines = (dlcContentSetAttributeInline,)

@admin.register(dlcContentSetAttribute)
class DlcContentSetAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "content_set", "name", "value")
    search_fields = ("name", "value", "content_set__dlc__tid")

@admin.register(titleContentSize)
class TitleContentSizeAdmin(admin.ModelAdmin):
    list_display = ("id", "app_tid", "content_size", "tmd_size", "max_content_index")
    search_fields = ("app_tid",)

@admin.register(ownedTitle)
class OwnedTitleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "ticketid", "version")
    search_fields = ("title__name", "title__tid", "owner__consoleid", "ticketid")
    autocomplete_fields = ("title", "owner")
    list_per_page = 50

@admin.register(ownedTicket)
class OwnedTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "owner", "ticketid")
    search_fields = ("item__itemcode", "item__name", "owner__consoleid", "ticketid")
    autocomplete_fields = ("item", "owner")

@admin.register(wishlistedTitle)
class WishlistedTitleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner")
    search_fields = ("title__name", "title__tid", "owner__consoleid")
    autocomplete_fields = ("title", "owner")

@admin.register(customTitleID)
class CustomTitleIDAdmin(admin.ModelAdmin):
    list_display = ("id", "tid", "related_to")
    search_fields = ("tid", "related_to__consoleid")
    autocomplete_fields = ("related_to",)

@admin.register(movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_3d", "time_in_sec", "new", "date")
    list_filter = ("is_3d", "new")
    search_fields = ("name",)

@admin.register(announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "date", "is_banner")
    list_filter = ("is_banner",)
    search_fields = ("title", "content")

@admin.register(motd)
class MotdAdmin(admin.ModelAdmin):
    list_display = ("id", "content", "order")
    search_fields = ("content",)

@admin.register(redeemableCard)
class RedeemableCardAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "used", "is_money", "content")
    list_filter = ("used", "is_money")
    search_fields = ("code", "content")

@admin.register(searchCategory)
class SearchCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "platform_list")
    search_fields = ("name", "platform_list")

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "voted_title", "age", "gender")
    list_filter = ("gender", "q4", "q5")
    search_fields = ("client__consoleid", "voted_title__name")
    autocomplete_fields = ("client", "voted_title")
from shopdeckdb import region_admin
