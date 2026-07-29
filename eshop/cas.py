from flask import Blueprint, request, render_template, make_response
import xmltodict, time, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopdeck.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from shopdeckdb.models import *
from django.core.exceptions import ObjectDoesNotExist

print("CAS Starting Up")

_UA_ALLOWED = {
    "CTR EC 040600 Mar 14 2012 13:32:39",
    "CTR NUP 040600 Mar 14 2012 13:32:39",
}

cas = Blueprint("cas", "cas")

def _xml(body):
    r = make_response(body)
    r.headers.set("Content-Type", "text/xml; charset=utf-8")
    return r

def _find_itemcode(filters):
    if isinstance(filters, dict):
        filters = [filters]
    if not isinstance(filters, list):
        return None
    for f in filters:
        if isinstance(f, dict) and f.get("cas:Name") == "sys.ItemCode":
            return f.get("cas:Value")
    return None

@cas.route("/cas/services/CatalogingSOAP", methods=['POST'])
def soap():
    raw = request.get_data()
    if raw == b"IwI":
        return "TwT"
    if request.headers.get('User-Agent') not in _UA_ALLOWED:
        return "Error"
    try:
        parsed = xmltodict.parse(raw)
    except Exception:
        return "Error"

    body = parsed.get('SOAP-ENV:Envelope', {}).get('SOAP-ENV:Body', {})
    now = int(round(time.time() * 1000))

    if "cas:ListTitlesEx" in body:
        req = body["cas:ListTitlesEx"]
        title_id = req.get("cas:TitleId")
        if isinstance(title_id, list):
            title_id = title_id[0] if title_id else ""
        title = Title.objects.filter(tid=title_id).order_by("id").first()
        if title is None:
            return "Error"
        csize = titleContentSize.objects.filter(app_tid=title_id).first()
        return _xml(render_template("cas/listTitlesEx.xml", id=req.get("cas:DeviceId"), message=req.get("cas:MessageId"), time=now, t=title, csize=csize))

    if "cas:GetContentSizes" in body:
        req = body["cas:GetContentSizes"]
        app_id = req.get("cas:TitleId", "")
        try:
            csize = titleContentSize.objects.get(app_tid=app_id)
        except ObjectDoesNotExist:
            return "Error"
        return _xml(render_template("cas/getContentSizes.xml", id=req.get("cas:DeviceId"), message=req.get("cas:MessageId"), time=now, c=csize))

    if "cas:ListContentSetsEx" in body:
        req = body["cas:ListContentSetsEx"]
        title_id = req.get("cas:TitleId")
        offset = int(req.get("cas:ListResultOffset", 0) or 0)
        requested_attrs = req.get("cas:Attributes", [])
        if isinstance(requested_attrs, str):
            requested_attrs = [requested_attrs]
        include_prices = "Prices" in requested_attrs
        itemcode = _find_itemcode(req.get("cas:AttributeFiltersEx", []))
        try:
            dlc = dlcContentTitle.objects.get(tid=title_id)
        except ObjectDoesNotExist:
            return "Error"
        sets = dlcContentSet.objects.filter(dlc=dlc).order_by("order", "id")
        if itemcode:
            sets = sets.filter(itemcode=itemcode)
        total = sets.count()
        if dlc.paginated and dlc.page_limit:
            sets = sets[offset:offset + dlc.page_limit]
            if not sets and offset != 0:
                return "Error"
        else:
            if offset != 0:
                return "Error"
        contents = []
        for s in sets:
            contents.append({
                "title_id": dlc.tid,
                "content_indexes": s.index_list(),
                "attributes": list(s.attributes.all()),
                "item_id": s.item_id,
                "price": s.price,
                "currency": s.currency,
            })
        return _xml(render_template("cas/contentsets.xml", id=req.get("cas:DeviceId"), message=req.get("cas:MessageId"), time=now, contents=contents, total=total, include_prices=include_prices))

    if "cas:ListItems" in body:
        req = body["cas:ListItems"]
        title_id = req.get("cas:TitleId")
        device_id = req.get("cas:DeviceId")
        msg_id = req.get("cas:MessageId")

        for badge_tid, badge_item_id in (
            ("0004000D00153500", 29),
            ("0004000D00153600", 28),
        ):
            if title_id == badge_tid:
                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <ListItemsResponse xmlns="urn:cas.wsapi.broadon.com">
      <Version>2.0</Version>
      <DeviceId>{device_id}</DeviceId>
      <MessageId>{msg_id}</MessageId>
      <TimeStamp>{now}</TimeStamp>
      <ErrorCode>0</ErrorCode>
      <ListResultTotalSize>1</ListResultTotalSize>
      <Items>
        <TitleId>{title_id}</TitleId>
        <Contents><TitleIncluded>true</TitleIncluded></Contents>
        <Attributes><Name>TitleVersion</Name><Value>0</Value></Attributes>
        <Attributes><Name>TitleType</Name><Value>CTR_TKT</Value></Attributes>
        <Attributes><Name>TitleKind</Name><Value>SERVICE</Value></Attributes>
        <Attributes><Name>sys.ItemCode</Name><Value>CTRVJTTA00000002</Value></Attributes>
        <Attributes><Name>InitialPurchaseOnly</Name><Value>false</Value></Attributes>
        <Attributes><Name>MaxServiceDays</Name><Value>0</Value></Attributes>
        <Prices>
          <ItemId>{badge_item_id}</ItemId>
          <Price><Amount>1.00</Amount><Currency>USD</Currency></Price>
          <Limits><Limits>1</Limits><LimitKind>CR</LimitKind></Limits>
          <LicenseKind>SERVICE</LicenseKind>
        </Prices>
      </Items>
    </ListItemsResponse>
  </soapenv:Body>
</soapenv:Envelope>"""
                return _xml(xml)

        title = Title.objects.filter(tid=title_id).order_by("id").first()
        if title is None:
            return "Error"
        itemcode = _find_itemcode(req.get("cas:AttributeFilters", []))
        if itemcode:
            items = item.objects.filter(title=title, itemcode=itemcode)
        else:
            items = item.objects.filter(title=title)
        return _xml(render_template("cas/listItems.xml", id=req.get("cas:DeviceId"), message=req.get("cas:MessageId"), time=now, items=items, length=items.count()))

    return "Error"
