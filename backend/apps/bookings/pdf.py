from decimal import Decimal

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak

from apps.core.models import SiteSettings
from apps.core.pdf import (
    CONTENT_W, brand_header, build_pdf, chips_row, info_grid, line_items, logo_path, p, section, site_dict,
)
from .dossier_pdf import append_voucher_document_pages
from .vehicle_data import booking_vehicle_snapshot


COPY = {
    "en": {"title": "Booking voucher", "created": "Created", "booking_status": "Booking status", "customer": "Customer", "name": "Name",
           "email": "Email", "phone": "Phone", "nationality": "Nationality", "vehicle": "Vehicle & rental",
           "vehicle_label": "Vehicle", "flight_label": "Flight", "arrival": "Arrival", "airport": "Airport",
           "duration": "Rental duration", "rate": "Daily rate", "transmission": "Transmission",
           "journey": "Pickup & return", "pickup": "Pickup", "return": "Return", "date": "Date and time",
           "location": "Location", "address": "Address", "instructions": "Instructions", "flight": "Arrival details",
           "price": "Price breakdown", "description": "Description", "qty": "Qty", "unit": "Unit price",
           "amount": "Amount", "subtotal": "Subtotal", "tax": "Tax", "total": "Total amount (USD)",
           "payment": "Payment", "method": "Payment method", "status": "Payment status", "paid": "Paid",
           "balance": "Balance due", "terms": "Important rental information", "contact": "Contact Rafiki Car Hire",
           "privacy": "Identity pages are private. Keep this voucher secure and do not forward it.",
           "footer": "Drive Zanzibar with Confidence"},
    "it": {"title": "Voucher di prenotazione", "created": "Creato il", "booking_status": "Stato della prenotazione", "customer": "Cliente", "name": "Nome",
           "email": "Email", "phone": "Telefono", "nationality": "Nazionalità", "vehicle": "Veicolo e noleggio",
           "vehicle_label": "Veicolo", "flight_label": "Volo", "arrival": "Arrivo", "airport": "Aeroporto",
           "duration": "Durata del noleggio", "rate": "Tariffa giornaliera", "transmission": "Cambio",
           "journey": "Ritiro e riconsegna", "pickup": "Ritiro", "return": "Riconsegna", "date": "Data e ora",
           "location": "Luogo", "address": "Indirizzo", "instructions": "Istruzioni", "flight": "Dettagli di arrivo",
           "price": "Dettaglio dei costi", "description": "Descrizione", "qty": "Qtà", "unit": "Prezzo unitario",
           "amount": "Importo", "subtotal": "Subtotale", "tax": "Imposte", "total": "Totale (USD)",
           "payment": "Pagamento", "method": "Metodo di pagamento", "status": "Stato del pagamento", "paid": "Pagato",
           "balance": "Saldo dovuto", "terms": "Informazioni importanti sul noleggio", "contact": "Contatta Rafiki Car Hire",
           "privacy": "Le pagine dei documenti sono private. Conserva questo voucher in modo sicuro e non inoltrarlo.",
           "footer": "Guida Zanzibar in tutta sicurezza"},
    "es": {"title": "Bono de reserva", "created": "Creado", "booking_status": "Estado de la reserva", "customer": "Cliente", "name": "Nombre",
           "email": "Correo electrónico", "phone": "Teléfono", "nationality": "Nacionalidad", "vehicle": "Vehículo y alquiler",
           "vehicle_label": "Vehículo", "flight_label": "Vuelo", "arrival": "Llegada", "airport": "Aeropuerto",
           "duration": "Duración del alquiler", "rate": "Tarifa diaria", "transmission": "Transmisión",
           "journey": "Recogida y devolución", "pickup": "Recogida", "return": "Devolución", "date": "Fecha y hora",
           "location": "Lugar", "address": "Dirección", "instructions": "Instrucciones", "flight": "Detalles de llegada",
           "price": "Desglose del precio", "description": "Descripción", "qty": "Cant.", "unit": "Precio unitario",
           "amount": "Importe", "subtotal": "Subtotal", "tax": "Impuestos", "total": "Total (USD)",
           "payment": "Pago", "method": "Método de pago", "status": "Estado del pago", "paid": "Pagado",
           "balance": "Saldo pendiente", "terms": "Información importante del alquiler", "contact": "Contacta con Rafiki Car Hire",
           "privacy": "Las páginas de identidad son privadas. Guarda este bono de forma segura y no lo reenvíes.",
           "footer": "Conduce Zanzibar con confianza"},
    "fr": {"title": "Bon de réservation", "created": "Créé le", "booking_status": "Statut de réservation", "customer": "Client", "name": "Nom",
           "email": "E-mail", "phone": "Téléphone", "nationality": "Nationalité", "vehicle": "Véhicule et location",
           "vehicle_label": "Véhicule", "flight_label": "Vol", "arrival": "Arrivée", "airport": "Aéroport",
           "duration": "Durée de location", "rate": "Tarif journalier", "transmission": "Transmission",
           "journey": "Prise en charge et retour", "pickup": "Prise en charge", "return": "Retour", "date": "Date et heure",
           "location": "Lieu", "address": "Adresse", "instructions": "Instructions", "flight": "Détails d'arrivée",
           "price": "Détail du prix", "description": "Description", "qty": "Qté", "unit": "Prix unitaire",
           "amount": "Montant", "subtotal": "Sous-total", "tax": "Taxes", "total": "Total (USD)",
           "payment": "Paiement", "method": "Mode de paiement", "status": "Statut du paiement", "paid": "Payé",
           "balance": "Solde dû", "terms": "Informations importantes sur la location", "contact": "Contacter Rafiki Car Hire",
           "privacy": "Les pages d'identité sont privées. Conservez ce bon en lieu sûr et ne le transférez pas.",
           "footer": "Conduisez à Zanzibar en toute confiance"},
    "de": {"title": "Buchungsgutschein", "created": "Erstellt", "booking_status": "Buchungsstatus", "customer": "Kunde", "name": "Name",
           "email": "E-Mail", "phone": "Telefon", "nationality": "Nationalität", "vehicle": "Fahrzeug und Miete",
           "vehicle_label": "Fahrzeug", "flight_label": "Flug", "arrival": "Ankunft", "airport": "Flughafen",
           "duration": "Mietdauer", "rate": "Tagessatz", "transmission": "Getriebe",
           "journey": "Abholung und Rückgabe", "pickup": "Abholung", "return": "Rückgabe", "date": "Datum und Uhrzeit",
           "location": "Ort", "address": "Adresse", "instructions": "Hinweise", "flight": "Ankunftsinformationen",
           "price": "Preisübersicht", "description": "Beschreibung", "qty": "Menge", "unit": "Einzelpreis",
           "amount": "Betrag", "subtotal": "Zwischensumme", "tax": "Steuern", "total": "Gesamtbetrag (USD)",
           "payment": "Zahlung", "method": "Zahlungsart", "status": "Zahlungsstatus", "paid": "Bezahlt",
           "balance": "Offener Betrag", "terms": "Wichtige Mietinformationen", "contact": "Rafiki Car Hire kontaktieren",
           "privacy": "Ausweisseiten sind vertraulich. Bewahren Sie diesen Voucher sicher auf und leiten Sie ihn nicht weiter.",
           "footer": "Sansibar sicher und entspannt entdecken"},
    "pt": {"title": "Voucher da reserva", "created": "Criado em", "booking_status": "Estado da reserva", "customer": "Cliente", "name": "Nome",
           "email": "Email", "phone": "Telefone", "nationality": "Nacionalidade", "vehicle": "Veículo e aluguer",
           "vehicle_label": "Veículo", "flight_label": "Voo", "arrival": "Chegada", "airport": "Aeroporto",
           "duration": "Duração do aluguer", "rate": "Preço diário", "transmission": "Transmissão",
           "journey": "Levantamento e devolução", "pickup": "Levantamento", "return": "Devolução", "date": "Data e hora",
           "location": "Local", "address": "Morada", "instructions": "Instruções", "flight": "Detalhes de chegada",
           "price": "Discriminação do preço", "description": "Descrição", "qty": "Qtd.", "unit": "Preço unitário",
           "amount": "Valor", "subtotal": "Subtotal", "tax": "Impostos", "total": "Total (USD)",
           "payment": "Pagamento", "method": "Método de pagamento", "status": "Estado do pagamento", "paid": "Pago",
           "balance": "Saldo em dívida", "terms": "Informações importantes sobre o aluguer", "contact": "Contactar a Rafiki Car Hire",
           "privacy": "As páginas de identificação são privadas. Guarde este voucher em segurança e não o reencaminhe.",
           "footer": "Explore Zanzibar com confiança"},
}


def render_confirmation_pdf(booking) -> bytes:
    """Render the saved booking snapshot as a private, multi-page customer voucher."""
    settings = SiteSettings.load()
    site = site_dict(settings)
    language = booking.language if booking.language in COPY else "en"
    text = COPY[language]
    vehicle = booking_vehicle_snapshot(booking)
    money = lambda value: f"${Decimal(str(value or 0)):,.2f}"
    accepted = booking.booking_status == "CONFIRMED"
    status_label = "ACCEPTED" if accepted else booking.get_booking_status_display()
    meta = [("Booking ref.", booking.booking_reference), (text["created"], booking.created_at.strftime("%d %b %Y"))]
    phone = site.get("business_phone") or "+255 715 518 980"
    email = site.get("business_email") or ""
    address = site.get("business_address") or "Abeid Amani Karume International Airport, Zanzibar, Tanzania"
    pickup_text = f"{booking.pickup_date:%d %b %Y} · {booking.pickup_time:%H:%M}"
    return_text = f"{booking.return_date:%d %b %Y} · {booking.return_time:%H:%M}"

    story = [
        brand_header(site, text["title"], meta, logo_path(settings)),
        chips_row([(text["booking_status"], status_label, "green" if accepted else "amber"),
                   (text["status"], booking.get_payment_status_display(), "green" if booking.payment_status == "PAID" else "amber")]),
        section(text["customer"]),
        info_grid([(text["name"], booking.customer.full_name), (text["email"], booking.customer.email),
                   (text["phone"], booking.customer.phone), (text["nationality"], booking.customer.nationality or "—")]),
        section(text["vehicle"]),
        info_grid([(text["vehicle_label"], f"{vehicle.get('name', 'Vehicle')} ({vehicle.get('brand', '')} {vehicle.get('model', '')})"),
                   (text["duration"], f"{booking.rental_days} day(s)"), (text["rate"], money(booking.daily_rate)),
                   (text["transmission"], vehicle.get("transmission_display") or vehicle.get("transmission") or "—")]),
        section(text["journey"]),
        info_grid([(text["pickup"], pickup_text), (text["location"], booking.location_label("pickup")),
                   (text["address"], booking.location_address("pickup") or "—"),
                   (text["return"], return_text), (text["location"], booking.location_label("return")),
                   (text["address"], booking.location_address("return") or "—")]),
        info_grid([(text["total"], money(booking.grand_total))]),
    ]
    flight = getattr(booking, "flight", None)
    if flight and (flight.airline_name or flight.flight_number):
        story += [section(text["flight"]), info_grid([
            (text["flight_label"], f"{flight.airline_name} {flight.flight_number}".strip()),
            (text["arrival"], f"{flight.arrival_date or ''} {flight.arrival_time or ''}".strip()),
            (text["airport"], flight.arrival_airport or "—"),
        ])]
    story += [section(text["contact"]), info_grid([
        (text["location"], address), (text["phone"], phone), (text["email"], email or "—"),
    ])]

    story += [
        PageBreak(),
        brand_header(site, text["price"], meta, logo_path(settings)),
        section(text["price"]),
    ]
    lines = booking.pricing_breakdown.get("lines", [])
    rows = [[line.get("description", ""), str(line.get("quantity", 1)), money(line.get("unit_price")), money(line.get("total"))]
            for line in lines]
    totals = [(text["subtotal"], money(booking.pricing_breakdown.get("subtotal", booking.grand_total)), False)]
    if booking.tax_amount:
        totals.append((text["tax"], money(booking.tax_amount), False))
    totals.append((text["total"], money(booking.grand_total), True))
    story.append(line_items([text["description"], text["qty"], text["unit"], text["amount"]], rows,
                            [100 * mm, 18 * mm, 31 * mm, 31 * mm], totals))
    story += [section(text["payment"]), info_grid([
        (text["method"], booking.get_payment_method_display()), (text["status"], booking.get_payment_status_display()),
        (text["paid"], money(booking.amount_paid)), (text["balance"], money(booking.balance_due)),
    ])]
    if settings.invoice_terms:
        story += [section(text["terms"]), p(settings.invoice_terms.replace("\n", "<br/>"), "small")]

    append_voucher_document_pages(story, booking)
    footer = " · ".join(x for x in (site.get("business_name"), phone, email, site.get("website")) if x)
    has_documents = booking.documents.exclude(verification_status="PURGED").exists()
    return build_pdf(story, title=f"{text['title']} {booking.booking_reference}", author=site["business_name"],
                     footer=footer, footer_note=text["privacy"] if has_documents else text["footer"])
