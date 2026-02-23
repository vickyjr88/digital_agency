"""
seed_tumanasi_zones.py
Run once to populate the tumanasi_zones table from Tumanasi's price list.
Usage:  python seed_tumanasi_zones.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database.config import SessionLocal
from database.tumanasi_models import TumansiZone
from database.models import Base
from database.config import engine
import uuid

# Ensure tables exist
Base.metadata.create_all(bind=engine)

ZONES = [
    # ── WITHIN CBD ───────────────────────────────────────────────────────────
    ("Within CBD", "Delivery (Within CBD)", 100),
    ("Within CBD", "Parcel Sending (CBD)", 100),
    ("Within CBD", "Goomba", 200),

    # ── WAIYAKI WAY ──────────────────────────────────────────────────────────
    ("Waiyaki Way", "Museum Hill", 200),
    ("Waiyaki Way", "Mauseaum Hill", 250),
    ("Waiyaki Way", "Chiromo", 300),
    ("Waiyaki Way", "Riverside", 300),
    ("Waiyaki Way", "ICEA Lion", 300),
    ("Waiyaki Way", "Mirage", 300),
    ("Waiyaki Way", "Westlands", 300),
    ("Waiyaki Way", "The Mall", 300),
    ("Waiyaki Way", "Rhapsody", 300),
    ("Waiyaki Way", "Sand Centre", 300),
    ("Waiyaki Way", "The Oval", 300),
    ("Waiyaki Way", "Westgate Mall", 300),
    ("Waiyaki Way", "Safaricom HQ", 350),
    ("Waiyaki Way", "The Adress", 350),
    ("Waiyaki Way", "ABC Place", 350),
    ("Waiyaki Way", "Quickmart Waruku", 400),
    ("Waiyaki Way", "White House", 400),
    ("Waiyaki Way", "Kangemi", 400),
    ("Waiyaki Way", "Loresho", 400),
    ("Waiyaki Way", "Kindaruma Mall", 450),
    ("Waiyaki Way", "Upper Kabete", 450),
    ("Waiyaki Way", "Ndumbuini", 500),
    ("Waiyaki Way", "Uthiru", 500),
    ("Waiyaki Way", "Rungiri", 600),
    ("Waiyaki Way", "Kinoo", 600),
    ("Waiyaki Way", "Regen", 600),
    ("Waiyaki Way", "Kikuyu", 800),
    ("Waiyaki Way", "Gitara", 1000),
    ("Waiyaki Way", "Limuru", 1500),
    ("Waiyaki Way", "Valley Rd", 300),
    ("Waiyaki Way", "Nairobi Hospital", 300),
    ("Waiyaki Way", "Huringham", 300),
    ("Waiyaki Way", "Yaya Centre", 300),
    ("Waiyaki Way", "Kileleshwa", 300),
    ("Waiyaki Way", "Valley Arcade", 350),
    ("Waiyaki Way", "Lavington", 400),
    ("Waiyaki Way", "Hatheru Rd", 400),
    ("Waiyaki Way", "Amboseli", 400),
    ("Waiyaki Way", "Kawangware", 500),

    # ── LOWER KABETE ─────────────────────────────────────────────────────────
    ("Lower Kabete", "Westside Towers", 300),
    ("Lower Kabete", "Ngorney S.P", 300),
    ("Lower Kabete", "S.P Business Park", 350),
    ("Lower Kabete", "Hill View", 450),
    ("Lower Kabete", "Farasi Lane", 500),
    ("Lower Kabete", "KCA", 500),
    ("Lower Kabete", "School of GVT", 600),
    ("Lower Kabete", "Lower Kabete S.Centre", 600),
    ("Lower Kabete", "Wangige", 600),
    ("Lower Kabete", "Kituru", 600),
    ("Lower Kabete", "Mwimuto", 600),

    # ── LIMURU RD ─────────────────────────────────────────────────────────────
    ("Limuru Rd", "Figtree", 200),
    ("Limuru Rd", "Jamhuri Sec", 200),
    ("Limuru Rd", "Slima Plaza", 250),
    ("Limuru Rd", "Parklands", 300),
    ("Limuru Rd", "Muthaiga Mini", 400),
    ("Limuru Rd", "Karura Forest", 400),
    ("Limuru Rd", "Muthaiga N1", 400),
    ("Limuru Rd", "Village Market", 400),
    ("Limuru Rd", "Runda", 500),
    ("Limuru Rd", "Langata Riviera", 500),
    ("Limuru Rd", "Ruaka", 500),
    ("Limuru Rd", "Ndenderu", 600),
    ("Limuru Rd", "Banana", 700),

    # ── KILIMANI ─────────────────────────────────────────────────────────────
    ("Kilimani", "Milimani Area", 250),
    ("Kilimani", "Milimani Law Courts", 250),
    ("Kilimani", "UoN", 300),
    ("Kilimani", "Unserhil", 300),
    ("Kilimani", "State House", 300),
    ("Kilimani", "Dennis Pritt", 300),
    ("Kilimani", "Lenanan Rd", 300),
    ("Kilimani", "Arboretum", 300),

    # ── NGONG ROAD ────────────────────────────────────────────────────────────
    ("Ngong Road", "Daystar University", 300),
    ("Ngong Road", "City Mortuary", 300),
    ("Ngong Road", "Coptic Hospital", 300),
    ("Ngong Road", "Prestige", 300),
    ("Ngong Road", "Quiver Kilimani", 350),
    ("Ngong Road", "Green House", 350),
    ("Ngong Road", "Adams Arcade", 350),
    ("Ngong Road", "Kibra", 350),
    ("Ngong Road", "Telcom House", 350),
    ("Ngong Road", "Jamhuri Estate", 400),
    ("Ngong Road", "Oladume Rd", 350),
    ("Ngong Road", "Rista Rd", 350),
    ("Ngong Road", "Junction Mall", 400),
    ("Ngong Road", "Meteorological Department", 400),
    ("Ngong Road", "Dagoretti Corner", 400),
    ("Ngong Road", "Show Ground", 400),
    ("Ngong Road", "Race Course", 450),
    ("Ngong Road", "Lenana", 550),
    ("Ngong Road", "Karen", 600),
    ("Ngong Road", "Waterfront Karen", 600),
    ("Ngong Road", "Karen End", 700),
    ("Ngong Road", "KCB Karen", 700),
    ("Ngong Road", "Kerarapon Rd (Kwa Railal)", 700),
    ("Ngong Road", "Runda Mall Ngong", 800),
    ("Ngong Road", "Emboullul", 800),
    ("Ngong Road", "Vet", 850),
    ("Ngong Road", "Zambia", 850),
    ("Ngong Road", "Maasai Mall Ngong", 900),
    ("Ngong Road", "Ngong Town", 900),
    ("Ngong Road", "Matasia", 1300),

    # ── NAIVASHA ROAD ────────────────────────────────────────────────────────
    ("Naivasha Road", "Dagoretti Corner Nai", 400),
    ("Naivasha Road", "Wanye Rd", 400),
    ("Naivasha Road", "Deliverance Church", 400),
    ("Naivasha Road", "Congo", 400),
    ("Naivasha Road", "Coast", 500),
    ("Naivasha Road", "Mlango Soko", 500),
    ("Naivasha Road", "Mayers", 500),
    ("Naivasha Road", "Riruta", 500),
    ("Naivasha Road", "Kabiria", 500),
    ("Naivasha Road", "Equity Kawangware", 500),
    ("Naivasha Road", "Precious Blood", 500),
    ("Naivasha Road", "Precious Gardens", 500),
    ("Naivasha Road", "Ndonyp", 700),
    ("Naivasha Road", "Walthaka", 700),
    ("Naivasha Road", "Dagoretti", 700),

    # ── THIKA ROAD ───────────────────────────────────────────────────────────
    ("Thika Road", "Ngara", 250),
    ("Thika Road", "Pangani", 300),
    ("Thika Road", "Muthaiga Thika", 300),
    ("Thika Road", "Eastleigh", 300),
    ("Thika Road", "NYS", 300),
    ("Thika Road", "Survey", 350),
    ("Thika Road", "Utaali University", 350),
    ("Thika Road", "KCA University", 350),
    ("Thika Road", "Allsopps", 400),
    ("Thika Road", "Babadogon", 400),
    ("Thika Road", "Rosters", 400),
    ("Thika Road", "Garden City", 400),
    ("Thika Road", "Ngumba Estate", 400),
    ("Thika Road", "Safari Park Hotel", 400),
    ("Thika Road", "USIU", 400),
    ("Thika Road", "Thome", 600),
    ("Thika Road", "Marurui", 600),
    ("Thika Road", "TRM", 400),

    # ── KIAMBU ROAD ──────────────────────────────────────────────────────────
    ("Kiambu Road", "Muthaga", 300),
    ("Kiambu Road", "Kenya Forest Service", 300),
    ("Kiambu Road", "DCI Head Quarters", 300),
    ("Kiambu Road", "Muthaiga North", 350),
    ("Kiambu Road", "Karura Forest Kiambu", 350),
    ("Kiambu Road", "Ridgeways", 400),
    ("Kiambu Road", "Runda Mall Kiambu", 400),
    ("Kiambu Road", "Four Ways", 400),
    ("Kiambu Road", "Paradise Lost", 450),
    ("Kiambu Road", "K Mall", 450),
    ("Kiambu Road", "Thindigua", 450),
    ("Kiambu Road", "KIMST", 450),
    ("Kiambu Road", "Kingili", 500),
    ("Kiambu Road", "Kiambu Town", 600),

    # ── MAGADI ROAD ──────────────────────────────────────────────────────────
    ("Magadi Road", "Catholic University", 500),
    ("Magadi Road", "Mukoma Rd", 500),
    ("Magadi Road", "Multimedia University", 500),
    ("Magadi Road", "Maasai Lodge", 700),
    ("Magadi Road", "Nkoroi", 800),
    ("Magadi Road", "Kiserian", 1200),

    # ── JUJA ROAD ────────────────────────────────────────────────────────────
    ("Juja Road", "Mlango Kubwa", 300),
    ("Juja Road", "Eastleigh Juja", 300),
    ("Juja Road", "Mathare", 300),
    ("Juja Road", "Huruma", 300),
    ("Juja Road", "Moi Airbase", 350),
    ("Juja Road", "Kariobangi", 450),
    ("Juja Road", "Dandora", 500),
    ("Juja Road", "Umoja", 400),

    # ── KANGUDO ROAD ─────────────────────────────────────────────────────────
    ("Kangudo Road", "Komarock", 500),
    ("Kangudo Road", "Kayole", 500),
    ("Kangudo Road", "Mama Lucy Hospital", 600),
    ("Kangudo Road", "Njiru", 600),
    ("Kangudo Road", "Chokaa", 800),
    ("Kangudo Road", "Ruai", 800),
    ("Kangudo Road", "Makongeni Kangudo", 1000),
    ("Kangudo Road", "Kamulu", 1200),
    ("Kangudo Road", "Joska", 1500),
    ("Kangudo Road", "Malaa", 1500),

    # ── OUTERING ROAD ────────────────────────────────────────────────────────
    ("Outering Road", "Donholm", 400),
    ("Outering Road", "Fedha", 400),
    ("Outering Road", "Nyayo Estate Embakasi", 500),
    ("Outering Road", "Pipeline", 400),
    ("Outering Road", "Embakasi", 490),
    ("Outering Road", "Utawala", 800),

    # ── MOMBASA ROAD ─────────────────────────────────────────────────────────
    ("Mombasa Road", "Highway Mall Mombasa", 250),
    ("Mombasa Road", "Bunyala Rd", 300),
    ("Mombasa Road", "Industrial Area", 350),
    ("Mombasa Road", "Enterprise Rd", 400),
    ("Mombasa Road", "Lungalunga Rd", 400),
    ("Mombasa Road", "Road ABC", 400),
    ("Mombasa Road", "South C", 300),
    ("Mombasa Road", "South B", 350),
    ("Mombasa Road", "Hotel Mombasa Rd", 300),
    ("Mombasa Road", "Nextgen Mall", 350),
    ("Mombasa Road", "Ole Serenei", 350),
    ("Mombasa Road", "Panari", 350),
    ("Mombasa Road", "Sameer Park", 350),
    ("Mombasa Road", "Laingata", 400),
    ("Mombasa Road", "Imara Daima", 400),
    ("Mombasa Road", "Kiangombe", 500),
    ("Mombasa Road", "Cabanas", 500),
    ("Mombasa Road", "JKIA", 600),
    ("Mombasa Road", "SGR Station", 600),
    ("Mombasa Road", "Gateway Mall", 700),
    ("Mombasa Road", "Syokimau", 700),
    ("Mombasa Road", "Katani", 800),
    ("Mombasa Road", "Greatwall Estate (Beijing Rd)", 700),
    ("Mombasa Road", "Mlolongo", 800),
    ("Mombasa Road", "Signature", 900),
    ("Mombasa Road", "Sabaki", 900),
    ("Mombasa Road", "Athriver", 1000),
    ("Mombasa Road", "Greatwall Athi River", 1000),
    ("Mombasa Road", "Kitengela", 1200),
    ("Mombasa Road", "Athi River Town", 1200),

    # ── LANG'ATA ROAD ────────────────────────────────────────────────────────
    ("Lang'ata Road", "Lang'ata Stadium", 250),
    ("Lang'ata Road", "Bunyala Road Langata", 250),
    ("Lang'ata Road", "Nairobi West", 300),
    ("Lang'ata Road", "T-Mall", 300),
    ("Lang'ata Road", "Italia Odinga Rd", 300),
    ("Lang'ata Road", "Mbotezuma", 300),
    ("Lang'ata Road", "Ngumo", 300),
    ("Lang'ata Road", "Kenyatta Market", 300),
    ("Lang'ata Road", "Nyayo Highrise", 300),
    ("Lang'ata Road", "Wilson Airport", 300),
    ("Lang'ata Road", "Weston Hotel", 300),
    ("Lang'ata Road", "Nairobi West Prison", 300),
    ("Lang'ata Road", "Carnivore", 350),
    ("Lang'ata Road", "Freedom Heights", 350),
    ("Lang'ata Road", "Phenom Estate", 350),
    ("Lang'ata Road", "Langata", 350),
    ("Lang'ata Road", "Swaminarayan", 350),
    ("Lang'ata Road", "Langata Barracks", 350),
    ("Lang'ata Road", "KWS", 400),
    ("Lang'ata Road", "Langata Cemetery", 400),
    ("Lang'ata Road", "Royal Park Estate", 400),
    ("Lang'ata Road", "Langata / Boman Prison", 400),
    ("Lang'ata Road", "St. Mary's Hospital", 500),
    ("Lang'ata Road", "Galleria", 500),
    ("Lang'ata Road", "Bomas", 600),
    ("Lang'ata Road", "One Stop Arcade", 600),
    ("Lang'ata Road", "Tangaza University", 600),
    ("Lang'ata Road", "Kenya School of Law", 600),
    ("Lang'ata Road", "Hardy", 600),
    ("Lang'ata Road", "Karen Hospital", 600),
    ("Lang'ata Road", "Ndege Rd", 600),
    ("Lang'ata Road", "Woolmark Business Park", 600),
    ("Lang'ata Road", "Karen Rd Langata", 600),
    ("Lang'ata Road", "Waterfront Karen", 600),

    # ── LUMUMBA DRIVE ────────────────────────────────────────────────────────
    ("Lumumba Drive", "Lumumba Drive", 400),
    ("Lumumba Drive", "Roysambu", 400),
    ("Lumumba Drive", "Zimmerman", 400),
    ("Lumumba Drive", "Githurai 44/45", 500),
    ("Lumumba Drive", "Jacaranda Estate", 500),
    ("Lumumba Drive", "Kamiti Prison", 600),
    ("Lumumba Drive", "Kahawa West", 600),
    ("Lumumba Drive", "Ku Referral", 600),
    ("Lumumba Drive", "Kamiti Corner", 700),
    ("Lumumba Drive", "Kamiti Law Courts", 700),
    ("Lumumba Drive", "Kijani Ridge", 800),
    ("Lumumba Drive", "Nover Pioneer School", 800),
    ("Lumumba Drive", "Old City", 800),
    ("Lumumba Drive", "OJ", 800),
    ("Lumumba Drive", "Kahawa Sukari / Wendani", 600),
    ("Lumumba Drive", "Mwihoko", 700),
    ("Lumumba Drive", "Kenyatta University", 700),
    ("Lumumba Drive", "Ruiru", 800),
    ("Lumumba Drive", "Kamakis", 800),
    ("Lumumba Drive", "Kenyatta Rd", 1000),
    ("Lumumba Drive", "Juja", 1000),
    ("Lumumba Drive", "Weiteltnie", 1200),
    ("Lumumba Drive", "Thika Town", 1500),
    ("Lumumba Drive", "Makongeni Lumumba", 1700),
    ("Lumumba Drive", "Kasarani", 500),
    ("Lumumba Drive", "Malwi", 600),
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(TumansiZone).count()
        if existing > 0:
            print(f"⚠️  Zones already seeded ({existing} rows). Skipping.")
            return

        zones = [
            TumansiZone(
                id        = str(uuid.uuid4()),
                zone_name = z[0],
                area_name = z[1],
                price_kes = z[2],
            )
            for z in ZONES
        ]
        db.bulk_save_objects(zones)
        db.commit()
        print(f"✅ Seeded {len(zones)} zones into tumanasi_zones.")
    except Exception as exc:
        db.rollback()
        print(f"❌ Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
