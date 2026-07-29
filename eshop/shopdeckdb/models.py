from django.db import models
from django.contrib.auth.models import AbstractUser

class Client3DS(models.Model):
    id = models.AutoField(primary_key=True)
    consoleid = models.CharField(max_length=12, null=False)
    devicecert_consoleid = models.CharField(max_length=8, null=True, blank=True)
    devicetoken = models.CharField(max_length=21, null=False)
    is_terminated = models.BooleanField(default=False)
    balance = models.IntegerField(default=2147483647)
    language = models.CharField(max_length=3, null=False)
    region = models.CharField(max_length=3, null=False)
    country = models.CharField(max_length=3, null=False)
    uniquekey = models.CharField(max_length=21, null=False)
    def __str__(self):
        return "3DS "+self.consoleid

class User(AbstractUser):
    linked_ds = models.ForeignKey(Client3DS, null=True, on_delete=models.CASCADE)

class customTitleID(models.Model):
    tid = models.CharField(max_length=18, null=False)
    related_to = models.ForeignKey(Client3DS, null=False, on_delete=models.CASCADE)
    def __str__(self):
        return "Title "+self.tid+" for user "+self.related_to.consoleid

class publisher(models.Model):
    id = models.AutoField(primary_key=True)
    publisher_name = models.CharField(max_length=200)
    def __str__(self):
        return self.publisher_name

class category(models.Model):
    id = models.AutoField(primary_key=True)
    index = models.IntegerField(default=0, null=False)
    name = models.CharField(max_length=200)
    standard = models.BooleanField(default=False)
    icon_url = models.TextField(null=False)
    banner_url = models.TextField(null=False)
    description = models.TextField(default="", blank=True, help_text="Optional description shown for this category.")
    new = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    regions = models.ManyToManyField('region', blank=True, help_text="Regions this category appears in. Leave empty to show in ALL regions.")
    countries = models.ManyToManyField('countryCode', blank=True, help_text="Countries this category appears in. Empty = hidden everywhere.")
    def __str__(self):
        return "Category "+self.name

class genre(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class platform(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class parentalControl(models.Model):
    id = models.AutoField(primary_key=True)
    parental_system_name = models.CharField(max_length=200, verbose_name="Rating system (e.g. ESRB, PEGI)")
    parental_system_id = models.IntegerField(default=0)
    age_name = models.CharField(max_length=200, verbose_name="Rating label (e.g. Everyone, Teen)")
    age_number = models.IntegerField(default=0, verbose_name="Minimum age")
    icon_url_normal = models.TextField(default="", blank=True)
    icon_url_small = models.TextField(default="", blank=True)
    descriptors = models.ManyToManyField('ratingDescriptor', blank=True)
    def __str__(self):
        return self.parental_system_name + " - " + self.age_name

class ratingDescriptor(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    icon_url = models.TextField(default="", blank=True)
    def __str__(self):
        return self.name

class regionGroup(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=8, unique=True, help_text="EU, US, JP")
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name

class countryCode(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3, help_text="ISO country code e.g. IT, FR, US")
    name = models.CharField(max_length=100, default="", blank=True)
    group = models.ForeignKey(regionGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="countries")
    def __str__(self):
        g = self.group.code if self.group else "?"
        return "["+g+"] "+self.code+(" - "+self.name if self.name else "")

class Title(models.Model):
    id = models.AutoField(primary_key=True)
    tid = models.CharField(max_length=16, null=False)
    name = models.CharField(max_length=200)
    desc = models.TextField(default="", null=False)
    thumbnail_url = models.TextField(null=False)
    icon_url = models.TextField(null=False)
    banner_url = models.TextField(null=False)
    publisher = models.ForeignKey(publisher, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True, null=False)
    product_code = models.CharField(max_length=200)
    new = models.BooleanField(default=True)
    public = models.BooleanField(default=True)
    category = models.ManyToManyField(category, blank=True)
    genre = models.ManyToManyField(genre)
    in_app_purchase = models.BooleanField(default=False)
    platform = models.ForeignKey(platform, null=False, on_delete=models.CASCADE)
    region = models.ForeignKey('region', null=True, blank=True, on_delete=models.DO_NOTHING)
    countries = models.ManyToManyField('countryCode', blank=True, help_text="Countries this title is available in. Empty = hidden everywhere.")
    parentalControl = models.ForeignKey('parentalControl', null=True, blank=True, on_delete=models.SET_NULL)
    price = models.IntegerField(default=0, null=False)
    version = models.IntegerField(default=1024)
    is_not_downloadable = models.BooleanField(default=False)
    size = models.BigIntegerField(default=0)
    ticket_available = models.BooleanField(default=True)
    demo = models.ForeignKey("Title", on_delete=models.DO_NOTHING, null=True, blank=True)
    copyright = models.CharField(max_length=200, default="", blank=True)
    players_from = models.IntegerField(default=1)
    players_to = models.IntegerField(default=1)
    on_sale = models.BooleanField(default=False)
    sale_price = models.IntegerField(default=0)
    release_date = models.DateField(null=True, blank=True, help_text="The title's release date (editable).")
    def __str__(self):
        return self.name+" by "+self.publisher.publisher_name+" published on "+str(self.date)

class item(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.ForeignKey(Title, null=False, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, default="", blank=True)
    itemcode = models.CharField(max_length=16)
    content_index = models.CharField(max_length=150, default="0", blank=True)
    nintendo_content_id = models.IntegerField(null=True, blank=True)
    price = models.IntegerField(default=0, null=False)
    limit = models.IntegerField(default=1, null=False)
    def __str__(self):
        label = self.name if self.name else self.itemcode
        return "Item "+str(self.id)+" ("+label+") for "+self.title.name

class movie(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    thumbnail_url = models.TextField(null=False)
    banner_url = models.TextField(null=False)
    is_3d = models.BooleanField(default=False)
    moflex_url = models.TextField(null=False)
    time_in_sec = models.IntegerField(null=False)
    date = models.DateField(auto_now_add=True, null=False)
    category = models.ForeignKey(category, on_delete=models.DO_NOTHING, null=True, blank=True)
    new = models.BooleanField(default=True, null=False)
    def __str__(self):
        return self.name

class ownedTitle(models.Model):
    title = models.ForeignKey(Title, null=False, on_delete=models.CASCADE)
    ticketid = models.CharField(max_length=16, null=False)
    version = models.IntegerField(null=False)
    owner = models.ForeignKey(Client3DS, null=False, on_delete=models.CASCADE)
    def __str__(self):
        return "Title "+self.title.name+" owned by "+self.owner.consoleid

class ownedTicket(models.Model):
    item = models.ForeignKey(item, null=False, on_delete=models.CASCADE)
    ticketid = models.CharField(max_length=16, null=False)
    owner = models.ForeignKey(Client3DS, null=False, on_delete=models.CASCADE)
    def __str__(self):
        return "Ticket "+self.item.itemcode+" owned by "+self.owner.consoleid

class wishlistedTitle(models.Model):
    title = models.ForeignKey(Title, null=False, on_delete=models.CASCADE)
    owner = models.ForeignKey(Client3DS, null=False, on_delete=models.CASCADE)
    def __str__(self):
        return "Wishlisted title "+self.title.name+" wanted by "+self.owner.consoleid

class announcement(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, null=False)
    content = models.TextField(null=False)
    date = models.DateTimeField(auto_now_add=True, null=False)
    is_banner = models.BooleanField(default=False)
    banner_url = models.TextField(null=True, blank=True)
    def __str__(self):
        return "Announcement "+self.title

class motd(models.Model):
    content = models.TextField(null=False)
    order = models.IntegerField(default=0)
    def __str__(self):
        return self.content

class redeemableCard(models.Model):
    code = models.CharField(max_length=16, null=False)
    used = models.BooleanField(default=False)
    is_money = models.BooleanField(default=True)
    content = models.CharField(max_length=16, null=False)
    def __str__(self):
        return self.code

class searchCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    platform_list = models.TextField(verbose_name="Platform List (seperate each platform by a comma)")
    def __str__(self):
        return self.name

class Vote(models.Model):
    client = models.ForeignKey(Client3DS, on_delete=models.CASCADE)
    voted_title = models.ForeignKey(Title, on_delete=models.CASCADE, null=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    q3 = models.CharField(max_length=10)
    q4 = models.BooleanField()
    q5 = models.BooleanField()

class dlcContentTitle(models.Model):
    id = models.AutoField(primary_key=True)
    tid = models.CharField(max_length=16, null=False, verbose_name="DLC Title ID")
    name = models.CharField(max_length=200, default="", blank=True)
    paginated = models.BooleanField(default=False)
    page_limit = models.IntegerField(null=True, blank=True)
    def __str__(self):
        label = self.name if self.name else self.tid
        return "DLC container "+label

class dlcContentSet(models.Model):
    id = models.AutoField(primary_key=True)
    dlc = models.ForeignKey(dlcContentTitle, null=False, on_delete=models.CASCADE, related_name="content_sets")
    order = models.IntegerField(default=0)
    content_indexes = models.CharField(max_length=255, default="", blank=True, verbose_name="Content indexes (comma separated)")
    itemcode = models.CharField(max_length=16, default="", blank=True)
    item_id = models.IntegerField(null=True, blank=True)
    price = models.CharField(max_length=16, default="0", blank=True)
    currency = models.CharField(max_length=8, default="CREDIT", blank=True)
    def index_list(self):
        return [c.strip() for c in self.content_indexes.split(",") if c.strip()]
    def __str__(self):
        return "Content set "+str(self.id)+" for "+self.dlc.tid

class dlcContentSetAttribute(models.Model):
    id = models.AutoField(primary_key=True)
    content_set = models.ForeignKey(dlcContentSet, null=False, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField(max_length=200, null=False)
    value = models.TextField(default="", blank=True)
    def __str__(self):
        return self.name+"="+self.value

class titleContentSize(models.Model):
    id = models.AutoField(primary_key=True)
    app_tid = models.CharField(max_length=16, null=False, verbose_name="Application Title ID")
    content_size = models.CharField(max_length=64, default="", blank=True)
    tmd_size = models.BigIntegerField(default=0)
    max_content_index = models.IntegerField(default=0)
    def __str__(self):
        return "Content size for "+self.app_tid

class region(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    initial = models.CharField(max_length=200, default="", blank=True)
    def __str__(self):
        return self.name

class screenshot(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="screenshots")
    url = models.TextField()
    order = models.IntegerField(default=0)
    def __str__(self):
        return "Screenshot for "+str(self.title_id)
