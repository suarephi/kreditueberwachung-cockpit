"""Bilingual column labels (DE/EN) for the Kreditüberwachung Cockpit.

Phase 1: covers every column from every business table so transposed
dossier views and ad-hoc dataframes get human-readable headers in either
language. Phase 2 (page titles, section headers, tooltips) follows
once column-level translation is approved.
"""
from __future__ import annotations
from typing import Iterable
import streamlit as st
import pandas as pd


SUPPORTED = ("de", "en")


# ---------------------------------------------------------------------------
# Per-table column dictionaries. Same keys in both DE and EN.
# ---------------------------------------------------------------------------
COLUMNS: dict[str, dict[str, dict[str, str]]] = {
    "client": {
        "de": {
            "client_id": "Kunden-ID", "external_ref": "Externe Referenz",
            "salutation": "Anrede", "first_name": "Vorname",
            "middle_name": "Zweitname", "last_name": "Nachname",
            "birth_name": "Geburtsname", "birth_date": "Geburtsdatum",
            "nationality": "Staatsangehörigkeit",
            "second_nationality": "Zweite Staatsangehörigkeit",
            "residence_permit": "Aufenthaltsbewilligung",
            "civil_status": "Zivilstand",
            "marital_property_regime": "Güterstand",
            "language_correspondence": "Korrespondenzsprache",
            "ahv_number": "AHV-Nummer", "email": "E-Mail",
            "phone_mobile": "Mobiltelefon", "phone_landline": "Festnetz",
            "iban": "IBAN", "profession": "Beruf",
            "employer": "Arbeitgeber", "noga_code": "NOGA-Code",
            "employment_type": "Anstellungsart",
            "employment_since": "Anstellung seit",
            "education_level": "Bildungsniveau",
            "segment": "Segment", "kyc_level": "KYC-Stufe",
            "kyc_review_date": "Letzte KYC-Prüfung",
            "pep_flag": "PEP-Flag", "sanctions_flag": "Sanktions-Flag",
            "sanctions_check_date": "Letzter Sanktions-Check",
            "source_of_funds": "Mittelherkunft",
            "customer_since": "Kunde seit",
            "address_id": "Adress-ID",
            "relationship_manager": "Kundenberater",
            "created_at": "Erstellt", "updated_at": "Geändert",
            "last_review_date": "Letztes Review",
        },
        "en": {
            "client_id": "Client ID", "external_ref": "External Ref",
            "salutation": "Salutation", "first_name": "First Name",
            "middle_name": "Middle Name", "last_name": "Last Name",
            "birth_name": "Birth Name", "birth_date": "Date of Birth",
            "nationality": "Nationality",
            "second_nationality": "Second Nationality",
            "residence_permit": "Residence Permit",
            "civil_status": "Marital Status",
            "marital_property_regime": "Property Regime",
            "language_correspondence": "Correspondence Language",
            "ahv_number": "Social Security No.", "email": "Email",
            "phone_mobile": "Mobile", "phone_landline": "Landline",
            "iban": "IBAN", "profession": "Profession",
            "employer": "Employer", "noga_code": "NOGA Code",
            "employment_type": "Employment Type",
            "employment_since": "Employed Since",
            "education_level": "Education Level",
            "segment": "Segment", "kyc_level": "KYC Level",
            "kyc_review_date": "Last KYC Review",
            "pep_flag": "PEP Flag", "sanctions_flag": "Sanctions Flag",
            "sanctions_check_date": "Last Sanctions Check",
            "source_of_funds": "Source of Funds",
            "customer_since": "Customer Since",
            "address_id": "Address ID",
            "relationship_manager": "Relationship Manager",
            "created_at": "Created", "updated_at": "Updated",
            "last_review_date": "Last Review",
        },
    },
    "address": {
        "de": {
            "address_id": "Adress-ID", "street": "Strasse",
            "house_number": "Hausnummer", "postal_code": "PLZ",
            "city": "Ort", "canton": "Kanton", "country": "Land",
            "bfs_gemeinde_nr": "BFS-Gemeinde-Nr.",
            "ms_region": "MS-Region", "address_type": "Adresstyp",
            "valid_from": "Gültig ab", "valid_to": "Gültig bis",
        },
        "en": {
            "address_id": "Address ID", "street": "Street",
            "house_number": "Number", "postal_code": "Postal Code",
            "city": "City", "canton": "Canton", "country": "Country",
            "bfs_gemeinde_nr": "BFS Municipality No.",
            "ms_region": "MS Region", "address_type": "Address Type",
            "valid_from": "Valid From", "valid_to": "Valid To",
        },
    },
    "household": {
        "de": {
            "household_id": "Haushalts-ID",
            "household_type": "Haushaltstyp",
            "dependents_count": "Anzahl Unterhaltsberechtigte",
            "children_count": "Anzahl Kinder",
            "children_ages": "Alter Kinder",
            "total_persons": "Personen total", "notes": "Bemerkungen",
        },
        "en": {
            "household_id": "Household ID",
            "household_type": "Household Type",
            "dependents_count": "Dependents",
            "children_count": "Children",
            "children_ages": "Children Ages",
            "total_persons": "Total Persons", "notes": "Notes",
        },
    },
    "property": {
        "de": {
            "property_id": "Objekt-ID", "object_type": "Objekttyp",
            "sub_type": "Untertyp", "address_id": "Adress-ID",
            "egid": "EGID", "ewid": "EWID",
            "construction_year": "Baujahr",
            "last_renovation_year": "Letzte Sanierung",
            "living_area_sqm": "Wohnfläche m²",
            "plot_area_sqm": "Grundstück m²",
            "rooms": "Zimmer", "bathrooms": "Bäder",
            "floors_total": "Stockwerke", "floor_unit": "Stockwerk Einheit",
            "heating_type": "Heizungsart", "heating_year": "Heizung Jahr",
            "geak_class": "GEAK-Klasse",
            "building_insurance_value": "GVZ-Wert",
            "annual_rental_income_chf": "Jährlicher Mietzins (CHF)",
            "commercial_use": "Gewerbliche Nutzung", "usage": "Nutzung",
            "micro_location_score": "Mikrolage-Score",
            "macro_location_score": "Makrolage-Score",
            "flood_zone": "Hochwasserzone", "noise_ruk": "Lärm RUK",
            "seismic_zone": "Erdbebenzone",
            "purchase_price": "Kaufpreis", "purchase_date": "Kaufdatum",
            "status": "Status", "region_code": "Region",
            "created_at": "Erstellt",
        },
        "en": {
            "property_id": "Property ID", "object_type": "Object Type",
            "sub_type": "Sub-type", "address_id": "Address ID",
            "egid": "EGID", "ewid": "EWID",
            "construction_year": "Construction Year",
            "last_renovation_year": "Last Renovation",
            "living_area_sqm": "Living Area sqm",
            "plot_area_sqm": "Plot Area sqm",
            "rooms": "Rooms", "bathrooms": "Bathrooms",
            "floors_total": "Floors", "floor_unit": "Unit Floor",
            "heating_type": "Heating Type", "heating_year": "Heating Year",
            "geak_class": "GEAK Class",
            "building_insurance_value": "Building Insurance Value",
            "annual_rental_income_chf": "Annual Rental Income (CHF)",
            "commercial_use": "Commercial Use", "usage": "Usage",
            "micro_location_score": "Micro-Location Score",
            "macro_location_score": "Macro-Location Score",
            "flood_zone": "Flood Zone", "noise_ruk": "Noise Class",
            "seismic_zone": "Seismic Zone",
            "purchase_price": "Purchase Price", "purchase_date": "Purchase Date",
            "status": "Status", "region_code": "Region",
            "created_at": "Created",
        },
    },
    "loan": {
        "de": {
            "loan_id": "Kredit-ID",
            "primary_client_id": "Hauptkunden-ID",
            "household_id": "Haushalts-ID", "property_id": "Objekt-ID",
            "origination_date": "Kreditbeginn",
            "first_drawdown_date": "Erstauszahlung",
            "original_amount": "Ursprungsbetrag",
            "current_outstanding": "Aktueller Saldo",
            "first_mortgage_amount": "1. Hypothek",
            "second_mortgage_amount": "2. Hypothek",
            "ltv_pct": "Belehnung %",
            "dsti_pct": "Tragbarkeit %",
            "pillar2_pledge": "Säule-2-Verpfändung",
            "pillar3a_pledge": "Säule-3a-Verpfändung",
            "pillar3a_indirect_amortization": "Indirekte Amortisation 3a",
            "status": "Status", "product_line": "Produktlinie",
            "currency": "Währung", "notes": "Bemerkungen",
        },
        "en": {
            "loan_id": "Loan ID",
            "primary_client_id": "Primary Client ID",
            "household_id": "Household ID", "property_id": "Property ID",
            "origination_date": "Origination Date",
            "first_drawdown_date": "First Drawdown",
            "original_amount": "Original Amount",
            "current_outstanding": "Current Outstanding",
            "first_mortgage_amount": "1st Mortgage",
            "second_mortgage_amount": "2nd Mortgage",
            "ltv_pct": "LTV %",
            "dsti_pct": "DSTI %",
            "pillar2_pledge": "Pillar 2 Pledge",
            "pillar3a_pledge": "Pillar 3a Pledge",
            "pillar3a_indirect_amortization": "Indirect Amort. via 3a",
            "status": "Status", "product_line": "Product Line",
            "currency": "Currency", "notes": "Notes",
        },
    },
    "tranche": {
        "de": {
            "tranche_id": "Tranchen-ID", "loan_id": "Kredit-ID",
            "tranche_type": "Tranchentyp", "amount": "Betrag",
            "interest_rate_pct": "Zinssatz %",
            "reference_rate": "Referenzzins", "margin_bp": "Marge bps",
            "rate_fixing_date": "Zinsfixierung",
            "rate_reset_date": "Zinsanpassung",
            "maturity_date": "Fälligkeit",
            "amortization_type": "Amortisationsart",
            "amortization_amount_yearly": "Amortisation pro Jahr",
            "status": "Status",
        },
        "en": {
            "tranche_id": "Tranche ID", "loan_id": "Loan ID",
            "tranche_type": "Tranche Type", "amount": "Amount",
            "interest_rate_pct": "Interest Rate %",
            "reference_rate": "Reference Rate", "margin_bp": "Margin bps",
            "rate_fixing_date": "Rate Fixing Date",
            "rate_reset_date": "Rate Reset Date",
            "maturity_date": "Maturity",
            "amortization_type": "Amortization Type",
            "amortization_amount_yearly": "Annual Amortization",
            "status": "Status",
        },
    },
    "valuation": {
        "de": {
            "valuation_id": "Bewertungs-ID", "property_id": "Objekt-ID",
            "valuation_date": "Bewertungsdatum",
            "valuation_method": "Methode",
            "market_value": "Marktwert",
            "mortgage_lending_value": "Belehnungswert",
            "confidence_band_low": "Konfidenz unten",
            "confidence_band_high": "Konfidenz oben",
            "micro_score": "Mikrolage", "macro_score": "Makrolage",
            "is_current": "Aktuell",
            "valuator_id": "Bewerter-ID",
            "valuator_name": "Bewerter", "notes": "Bemerkungen",
        },
        "en": {
            "valuation_id": "Valuation ID", "property_id": "Property ID",
            "valuation_date": "Valuation Date",
            "valuation_method": "Method",
            "market_value": "Market Value",
            "mortgage_lending_value": "Mortgage Lending Value",
            "confidence_band_low": "Confidence Low",
            "confidence_band_high": "Confidence High",
            "micro_score": "Micro Score", "macro_score": "Macro Score",
            "is_current": "Current",
            "valuator_id": "Valuator ID",
            "valuator_name": "Valuator", "notes": "Notes",
        },
    },
    "income": {
        "de": {
            "income_id": "Einkommens-ID", "client_id": "Kunden-ID",
            "reporting_year": "Berichtsjahr",
            "gross_salary": "Bruttolohn",
            "bonus_avg_3y": "Ø Bonus 3 J.",
            "variable_income": "Variables Einkommen",
            "rental_income": "Mietzinseinnahmen",
            "dividend_income": "Dividenden",
            "pension_income": "Renten",
            "other_income": "Sonstige Einkünfte",
            "alimony_received": "Alimente erhalten",
            "alimony_paid": "Alimente bezahlt",
            "existing_debt_payments": "Bestehende Schuldverpflichtungen",
            "documented_via": "Belegt durch",
            "currency": "Währung", "confidence": "Verlässlichkeit",
        },
        "en": {
            "income_id": "Income ID", "client_id": "Client ID",
            "reporting_year": "Reporting Year",
            "gross_salary": "Gross Salary",
            "bonus_avg_3y": "3y Avg Bonus",
            "variable_income": "Variable Income",
            "rental_income": "Rental Income",
            "dividend_income": "Dividends",
            "pension_income": "Pensions",
            "other_income": "Other Income",
            "alimony_received": "Alimony Received",
            "alimony_paid": "Alimony Paid",
            "existing_debt_payments": "Existing Debt Service",
            "documented_via": "Documented Via",
            "currency": "Currency", "confidence": "Confidence",
        },
    },
    "affordability_assessment": {
        "de": {
            "assessment_id": "Bewertungs-ID", "loan_id": "Kredit-ID",
            "assessment_date": "Bewertungsdatum",
            "imputed_interest_rate": "Kalk. Zinssatz",
            "maintenance_rate": "Unterhaltspauschale",
            "amortization_required": "Amortisation",
            "total_cost_yearly": "Total Kosten p.a.",
            "household_income_used": "Verwendetes Einkommen",
            "income_basis": "Cashflow-Basis",
            "dsti_calculated": "Tragbarkeit %",
            "dsti_threshold": "Schwelle %",
            "pass_fail": "Resultat",
            "exception_approval_id": "Ausnahmegenehmigung",
        },
        "en": {
            "assessment_id": "Assessment ID", "loan_id": "Loan ID",
            "assessment_date": "Assessment Date",
            "imputed_interest_rate": "Imputed Interest Rate",
            "maintenance_rate": "Maintenance Rate",
            "amortization_required": "Amortization",
            "total_cost_yearly": "Total Yearly Cost",
            "household_income_used": "Income Used",
            "income_basis": "Cashflow Basis",
            "dsti_calculated": "DSTI %",
            "dsti_threshold": "Threshold %",
            "pass_fail": "Result",
            "exception_approval_id": "Exception Approval",
        },
    },
    "risk_metrics": {
        "de": {
            "metric_id": "Metrik-ID", "loan_id": "Kredit-ID",
            "as_of_date": "Stichtag",
            "pd_1y": "PD 1 Jahr", "lgd": "LGD",
            "ead": "EAD", "expected_loss": "Erwarteter Verlust",
            "rating_internal": "Internes Rating",
            "watchlist_flag": "Beobachtungsliste",
            "npl_flag": "NPL-Flag",
            "forbearance_flag": "Forbearance-Flag",
            "days_past_due": "Tage überfällig",
            "covenant_breach_flag": "Covenant-Verletzung",
        },
        "en": {
            "metric_id": "Metric ID", "loan_id": "Loan ID",
            "as_of_date": "As-of Date",
            "pd_1y": "PD 1 Year", "lgd": "LGD",
            "ead": "EAD", "expected_loss": "Expected Loss",
            "rating_internal": "Internal Rating",
            "watchlist_flag": "Watchlist",
            "npl_flag": "NPL Flag",
            "forbearance_flag": "Forbearance Flag",
            "days_past_due": "Days Past Due",
            "covenant_breach_flag": "Covenant Breach",
        },
    },
    "event": {
        "de": {
            "event_id": "Event-ID", "loan_id": "Kredit-ID",
            "client_id": "Kunden-ID", "property_id": "Objekt-ID",
            "event_type": "Event-Typ", "event_subtype": "Untertyp",
            "severity": "Severity", "source": "Quelle",
            "detected_at": "Erkannt", "occurred_at": "Eingetreten",
            "title": "Titel", "description": "Beschreibung",
            "status": "Status", "assigned_to": "Zugewiesen an",
            "resolved_at": "Erledigt am",
            "sla_due_date": "SLA-Frist", "sla_basis": "SLA-Basis",
            "linked_case_id": "Verknüpfter Fall",
        },
        "en": {
            "event_id": "Event ID", "loan_id": "Loan ID",
            "client_id": "Client ID", "property_id": "Property ID",
            "event_type": "Event Type", "event_subtype": "Subtype",
            "severity": "Severity", "source": "Source",
            "detected_at": "Detected", "occurred_at": "Occurred",
            "title": "Title", "description": "Description",
            "status": "Status", "assigned_to": "Assigned To",
            "resolved_at": "Resolved",
            "sla_due_date": "SLA Due", "sla_basis": "SLA Basis",
            "linked_case_id": "Linked Case",
        },
    },
    "loan_case": {
        "de": {
            "case_id": "Fall-ID", "case_type": "Falltyp",
            "loan_id": "Kredit-ID", "client_id": "Kunden-ID",
            "opened_at": "Eröffnet", "due_date": "Frist",
            "closed_at": "Geschlossen", "status": "Status",
            "priority": "Priorität", "assigned_team": "Team",
            "assigned_officer": "Bearbeiter",
            "decision": "Entscheidung", "decision_at": "Entschieden am",
            "decided_by": "Entschieden von", "notes": "Bemerkungen",
        },
        "en": {
            "case_id": "Case ID", "case_type": "Case Type",
            "loan_id": "Loan ID", "client_id": "Client ID",
            "opened_at": "Opened", "due_date": "Due Date",
            "closed_at": "Closed", "status": "Status",
            "priority": "Priority", "assigned_team": "Team",
            "assigned_officer": "Officer",
            "decision": "Decision", "decision_at": "Decided At",
            "decided_by": "Decided By", "notes": "Notes",
        },
    },
    "document": {
        "de": {
            "document_id": "Dokument-ID",
            "parent_type": "Bezugstyp", "parent_id": "Bezugs-ID",
            "doc_type": "Dokumenttyp", "filename": "Dateiname",
            "upload_date": "Upload",
            "expiry_date": "Ablaufdatum",
            "status": "Status", "hash": "Hash",
        },
        "en": {
            "document_id": "Document ID",
            "parent_type": "Parent Type", "parent_id": "Parent ID",
            "doc_type": "Doc Type", "filename": "Filename",
            "upload_date": "Upload",
            "expiry_date": "Expiry",
            "status": "Status", "hash": "Hash",
        },
    },
    "audit_log": {
        "de": {
            "audit_id": "Audit-ID", "entity_type": "Entitätstyp",
            "entity_id": "Entitäts-ID", "field_name": "Feld",
            "old_value": "Vorher", "new_value": "Nachher",
            "changed_by": "Geändert von", "changed_at": "Geändert am",
            "source_system": "Quellsystem",
        },
        "en": {
            "audit_id": "Audit ID", "entity_type": "Entity Type",
            "entity_id": "Entity ID", "field_name": "Field",
            "old_value": "Old Value", "new_value": "New Value",
            "changed_by": "Changed By", "changed_at": "Changed At",
            "source_system": "Source System",
        },
    },
    "portfolio": {
        "de": {
            "portfolio_id": "Depot-ID", "client_id": "Kunden-ID",
            "strategy": "Strategie", "benchmark": "Benchmark",
            "inception_date": "Eröffnungsdatum",
            "total_value_chf": "Volumen (CHF)",
            "cash_chf": "Cash (CHF)",
            "ytd_return_pct": "YTD-Rendite %",
            "one_year_return_pct": "1-Jahres-Rendite %",
            "custodian": "Depotbank", "fee_model": "Gebührenmodell",
            "last_review_date": "Letztes Review",
        },
        "en": {
            "portfolio_id": "Portfolio ID", "client_id": "Client ID",
            "strategy": "Strategy", "benchmark": "Benchmark",
            "inception_date": "Inception Date",
            "total_value_chf": "Total Value (CHF)",
            "cash_chf": "Cash (CHF)",
            "ytd_return_pct": "YTD Return %",
            "one_year_return_pct": "1-Year Return %",
            "custodian": "Custodian", "fee_model": "Fee Model",
            "last_review_date": "Last Review",
        },
    },
    "position": {
        "de": {
            "position_id": "Positions-ID", "portfolio_id": "Depot-ID",
            "isin": "ISIN", "name": "Instrument",
            "asset_class": "Asset-Klasse", "currency": "Währung",
            "quantity": "Menge", "avg_cost_chf": "Ø Einstand (CHF)",
            "market_price_chf": "Kurs (CHF)",
            "market_value_chf": "Marktwert (CHF)",
            "unrealized_pnl_chf": "Unrealisierter G/V (CHF)",
            "weight_pct": "Gewicht %",
            "last_price_date": "Kursdatum",
        },
        "en": {
            "position_id": "Position ID", "portfolio_id": "Portfolio ID",
            "isin": "ISIN", "name": "Instrument",
            "asset_class": "Asset Class", "currency": "Currency",
            "quantity": "Quantity", "avg_cost_chf": "Avg Cost (CHF)",
            "market_price_chf": "Price (CHF)",
            "market_value_chf": "Market Value (CHF)",
            "unrealized_pnl_chf": "Unrealized P&L (CHF)",
            "weight_pct": "Weight %",
            "last_price_date": "Price Date",
        },
    },
    "account": {
        "de": {
            "account_id": "Konto-ID", "client_id": "Kunden-ID",
            "iban": "IBAN", "account_type": "Kontotyp",
            "currency": "Währung", "opened_date": "Eröffnet",
            "current_balance_chf": "Saldo (CHF)",
            "avg_balance_12m_chf": "Ø Saldo 12 Mt (CHF)",
            "status": "Status",
        },
        "en": {
            "account_id": "Account ID", "client_id": "Client ID",
            "iban": "IBAN", "account_type": "Account Type",
            "currency": "Currency", "opened_date": "Opened",
            "current_balance_chf": "Balance (CHF)",
            "avg_balance_12m_chf": "Avg Balance 12m (CHF)",
            "status": "Status",
        },
    },
    "account_tx": {
        "de": {
            "tx_id": "Tx-ID", "account_id": "Konto-ID",
            "tx_date": "Buchungsdatum", "value_date": "Valuta",
            "amount_chf": "Betrag (CHF)", "category": "Kategorie",
            "counterparty": "Gegenpartei",
            "description": "Beschreibung", "reference": "Referenz",
        },
        "en": {
            "tx_id": "Tx ID", "account_id": "Account ID",
            "tx_date": "Booking Date", "value_date": "Value Date",
            "amount_chf": "Amount (CHF)", "category": "Category",
            "counterparty": "Counterparty",
            "description": "Description", "reference": "Reference",
        },
    },
}


# Flatten for ad-hoc lookups (when caller only knows the column name).
FLAT: dict[str, dict[str, str]] = {"de": {}, "en": {}}
for table, langs in COLUMNS.items():
    for lang, mapping in langs.items():
        # Don't overwrite earlier definitions (the loan_id label from 'loan'
        # wins over a later table's loan_id).
        for k, v in mapping.items():
            FLAT[lang].setdefault(k, v)


# ---------------------------------------------------------------------------
# UI strings (small set; expanded in Phase 2)
# ---------------------------------------------------------------------------
UI: dict[str, dict[str, str]] = {
    "de": {
        "language_label": "Sprache",
        "lang_de": "Deutsch",
        "lang_en": "English",
        "tab_loan_tranches": "Kredit & Tranchen",
        "tab_property_valuation": "Objekt & Bewertungen",
        "tab_affordability": "Tragbarkeit",
        "tab_risk_metrics": "Risikokennzahlen",
        "tab_events": "Ereignisse",
        "tab_cases": "Fälle",
        "tab_documents": "Dokumente",
        "tab_household_income": "Haushaltseinkommen",
        "tab_accounts_tx": "Konten & Bewegungen",
    },
    "en": {
        "language_label": "Language",
        "lang_de": "Deutsch",
        "lang_en": "English",
        "tab_loan_tranches": "Loan & Tranches",
        "tab_property_valuation": "Property & Valuations",
        "tab_affordability": "Affordability",
        "tab_risk_metrics": "Risk Metrics",
        "tab_events": "Events",
        "tab_cases": "Cases",
        "tab_documents": "Documents",
        "tab_household_income": "Household Income",
        "tab_accounts_tx": "Accounts & Movements",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def current_lang() -> str:
    """Return the active language code from the URL ('de' default)."""
    raw = (st.query_params.get("lang") or "de").lower()
    return raw if raw in SUPPORTED else "de"


def t(key: str, lang: str | None = None) -> str:
    lang = lang or current_lang()
    return UI.get(lang, UI["de"]).get(key, key)


def col(name: str, table: str | None = None, lang: str | None = None) -> str:
    """Translate a single column name. If table is given, use its specific
    dictionary; otherwise fall back to the flattened lookup."""
    lang = lang or current_lang()
    if table and table in COLUMNS and name in COLUMNS[table].get(lang, {}):
        return COLUMNS[table][lang][name]
    return FLAT.get(lang, {}).get(name, name)


def rename(df: pd.DataFrame, table: str | None = None,
           lang: str | None = None) -> pd.DataFrame:
    """Return a copy of *df* with column names translated. Unknown columns
    are left untouched, so existing callers keep working."""
    if df is None or df.empty:
        return df
    lang = lang or current_lang()
    mapping = (COLUMNS.get(table, {}).get(lang, {})
               if table else FLAT.get(lang, {}))
    return df.rename(columns={c: mapping[c] for c in df.columns if c in mapping})


def index_de_en(idx: Iterable[str], lang: str | None = None,
                table: str | None = None) -> list[str]:
    """Translate an index of column names (used by .T transposed views)."""
    lang = lang or current_lang()
    mapping = (COLUMNS.get(table, {}).get(lang, {})
               if table else FLAT.get(lang, {}))
    return [mapping.get(c, c) for c in idx]
