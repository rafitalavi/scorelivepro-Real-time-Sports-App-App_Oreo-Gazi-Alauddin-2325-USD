import os
import re
import firebase_admin
from firebase_admin import messaging, credentials
from django.conf import settings
from .models import NotificationLog

def translate_notification(title, body, event_type, lang):
    if lang == 'en':
        return title, body

    translations = {
        'es': {
            'goal_title': "⚽ ¡Gol de {team}!",
            'goal_body': "Marcador actual: {home} {score} {away}",
            'ft_title': "🏁 Final del partido",
            'ft_body': "Resultado final: {home} {score} {away}",
            'lineup_title': "📋 Alineaciones confirmadas",
            'lineup_body': "El once inicial ya está disponible para el {home} vs {away}",
            'schedule_title': "📅 Calendario de {league}",
            'schedule_body': "Hay {count} partidos mañana en {league}. ¡No te los pierdas!",
            'match_start_title': "⏳ Empieza pronto",
            'match_start_body': "El partido comienza en 15 minutos: {home} vs {away}",
            'card_yellow_title': "🟨 ¡Tarjeta amarilla para {player} ({team})!",
            'card_red_title': "🟥 ¡Tarjeta roja para {player} ({team})!",
            'card_body': "{player} recibió una tarjeta en el minuto {time}'.",
            'sub_title': "🔄 Cambio en {team}",
            'sub_body': "Entra: {player_in} | Sale: {player_out} ({time}')",
            'var_title': "🖥️ Decisión del VAR: {team}",
            'var_body': "{detail} ({time}')",
        },
        'fr': {
            'goal_title': "⚽ But de {team} !",
            'goal_body': "Score actuel : {home} {score} {away}",
            'ft_title': "🏁 Fin du match",
            'ft_body': "Résultat final : {home} {score} {away}",
            'lineup_title': "📋 Compositions disponibles",
            'lineup_body': "Le onze de départ est disponible pour {home} vs {away}",
            'schedule_title': "📅 Calendrier de {league}",
            'schedule_body': "Il y a {count} matchs demain en {league}. Ne les manquez pas !",
            'match_start_title': "⏳ Coup d'envoi imminent",
            'match_start_body': "Le match commence dans 15 min : {home} vs {away}",
            'card_yellow_title': "🟨 Carton jaune pour {player} ({team}) !",
            'card_red_title': "🟥 Carton rouge pour {player} ({team}) !",
            'card_body': "{player} a reçu un carton à la {time}' minute.",
            'sub_title': "🔄 Remplacement pour {team}",
            'sub_body': "Entrant : {player_in} | Sortant : {player_out} ({time}')",
            'var_title': "🖥️ Décision de la VAR : {team}",
            'var_body': "{detail} ({time}')",
        },
        'de': {
            'goal_title': "⚽ Tor für {team}!",
            'goal_body': "Aktueller Spielstand: {home} {score} {away}",
            'ft_title': "🏁 Spielende",
            'ft_body': "Endergebnis: {home} {score} {away}",
            'lineup_title': "📋 Aufstellungen bestätigt",
            'lineup_body': "Die Startaufstellung für {home} gegen {away} ist jetzt verfügbar",
            'schedule_title': "📅 Spielplan für {league}",
            'schedule_body': "Morgen stehen {count} Spiele in {league} an. Verpasse es nicht!",
            'match_start_title': "⏳ Anpfiff in Kürze",
            'match_start_body': "Das Spiel beginnt in 15 Minuten: {home} gegen {away}",
            'card_yellow_title': "🟨 Gelbe Karte für {player} ({team})!",
            'card_red_title': "🟥 Rote Karte für {player} ({team})!",
            'card_body': "{player} erhielt eine karte in der {time}'. Minute.",
            'sub_title': "🔄 Auswechslung bei {team}",
            'sub_body': "Ein: {player_in} | Aus: {player_out} ({time}')",
            'var_title': "🖥️ VAR-Entscheidung: {team}",
            'var_body': "{detail} ({time}')",
        },
        'it': {
            'goal_title': "⚽ Gol di {team}!",
            'goal_body': "Risultato attuale: {home} {score} {away}",
            'ft_title': "🏁 Fischio finale",
            'ft_body': "Risultato finale: {home} {score} {away}",
            'lineup_title': "📋 Formazioni ufficiali",
            'lineup_body': "L'undici titolare è ora disponibile per {home} vs {away}",
            'schedule_title': "📅 Calendario {league}",
            'schedule_body': "Ci sono {count} partite domani in {league}. Non perdere l'appuntamento!",
            'match_start_title': "⏳ Calcio d'inizio imminente",
            'match_start_body': "La partita inizia tra 15 minuti: {home} vs {away}",
            'card_yellow_title': "🟨 Cartellino giallo per {player} ({team})!",
            'card_red_title': "🟥 Cartellino rosso per {player} ({team})!",
            'card_body': "{player} ha ricevuto un cartellino al minuto {time}'.",
            'sub_title': "🔄 Sostituzione per il {team}",
            'sub_body': "Entra: {player_in} | Esce: {player_out} ({time}')",
            'var_title': "🖥️ Decisione VAR: {team}",
            'var_body': "{detail} ({time}')",
        },
        'pt': {
            'goal_title': "⚽ Golo de {team}!",
            'goal_body': "Resultado atual: {home} {score} {away}",
            'ft_title': "🏁 Fim do jogo",
            'ft_body': "Resultado final: {home} {score} {away}",
            'lineup_title': "📋 Escalações confirmadas",
            'lineup_body': "A escalação inicial já está disponível para {home} vs {away}",
            'schedule_title': "📅 Jogos de {league}",
            'schedule_body': "Há {count} jogos amanhã em {league}. Não perca!",
            'match_start_title': "⏳ Início em breve",
            'match_start_body': "O jogo começa em 15 minutos: {home} vs {away}",
            'card_yellow_title': "🟨 Cartão amarelo para {player} ({team})!",
            'card_red_title': "🟥 Cartão vermelho para {player} ({team})!",
            'card_body': "{player} recebeu um cartão no minuto {time}'.",
            'sub_title': "🔄 Substituição no {team}",
            'sub_body': "Entra: {player_in} | Sai: {player_out} ({time}')",
            'var_title': "🖥️ Decisão do VAR: {team}",
            'var_body': "{detail} ({time}')",
        },
        'tr': {
            'goal_title': "⚽ {team} Gol Attı!",
            'goal_body': "Mevcut Skor: {home} {score} {away}",
            'ft_title': "🏁 Maç Sonucu",
            'ft_body': "Maç Sonucu: {home} {score} {away}",
            'lineup_title': "📋 İlk 11'ler Belli Oldu",
            'lineup_body': "{home} - {away} karşılaşmasının ilk 11'leri açıklandı",
            'schedule_title': "📅 {league} Fikstürü",
            'schedule_body': "Yarın {league} liginde {count} maç oynanacak. Kaçırmayın!",
            'match_start_title': "⏳ Başlamasına Az Kaldı",
            'match_start_body': "Karşılaşma 15 dakika içinde başlayacak: {home} - {away}",
            'card_yellow_title': "🟨 {player} Sarı Kart Gördü ({team})!",
            'card_red_title': "🟥 {player} Kırmızı Kart Gördü ({team})!",
            'card_body': "{player} {time}'. dakikada kart gördü.",
            'sub_title': "🔄 {team} Takımında Oyuncu Değişikliği",
            'sub_body': "Giren: {player_in} | Çıkan: {player_out} ({time}')",
            'var_title': "🖥️ VAR Kararı: {team}",
            'var_body': "{detail} ({time}')",
        }
    }

    t_map = translations.get(lang)
    if not t_map:
        return title, body

    if event_type == 'GOAL':
        m_title = re.search(r"(?:Goal by|Gol di|But de|Tor für)\s+(.+?)(?:\!|$)", title, re.IGNORECASE)
        team = m_title.group(1).strip() if m_title else ""
        m_body = re.search(r"(?:Score|Result|Risultato|Spielstand|Marcador).*?:\s*(.+?)\s+(\d+[\s-]*\d+)\s+(.+)", body, re.IGNORECASE)
        if m_body:
            home, score, away = m_body.group(1).strip(), m_body.group(2).strip(), m_body.group(3).strip()
        else:
            clean_body = re.sub(r"^.*?:", "", body).strip()
            score_match = re.search(r"(\d+[\s-]*\d+)", clean_body)
            if score_match:
                score = score_match.group(1).strip()
                parts = clean_body.split(score)
                home = parts[0].strip()
                away = parts[1].strip() if len(parts) > 1 else ""
            else:
                home, score, away = "", "", ""
        new_title = t_map['goal_title'].format(team=team)
        new_body = t_map['goal_body'].format(home=home, score=score, away=away)
        return new_title, new_body

    elif event_type == 'FULL_TIME':
        m_body = re.search(r"(?:Result|Risultato|Spielstand|Marcador).*?:\s*(.+?)\s+(\d+[\s-]*\d+)\s+(.+)", body, re.IGNORECASE)
        if m_body:
            home, score, away = m_body.group(1).strip(), m_body.group(2).strip(), m_body.group(3).strip()
        else:
            clean_body = re.sub(r"^.*?:", "", body).strip()
            score_match = re.search(r"(\d+[\s-]*\d+)", clean_body)
            if score_match:
                score = score_match.group(1).strip()
                parts = clean_body.split(score)
                home = parts[0].strip()
                away = parts[1].strip() if len(parts) > 1 else ""
            else:
                home, score, away = "", "", ""
        new_title = t_map['ft_title']
        new_body = t_map['ft_body'].format(home=home, score=score, away=away)
        return new_title, new_body

    elif event_type == 'LINEUPS':
        m_body = re.search(r"(?:available for|disponible pour|bestätigt für|disponibile per|açıklandı)\s*(.+?)\s+(?:vs|-)\s+(.+)", body, re.IGNORECASE)
        if m_body:
            home, away = m_body.group(1).strip(), m_body.group(2).strip()
        else:
            clean_body = re.sub(r"^.*?for\s+", "", body, flags=re.IGNORECASE).strip()
            parts = re.split(r"\s+(?:vs|-)\s+", clean_body, flags=re.IGNORECASE)
            home = parts[0].strip() if len(parts) > 0 else ""
            away = parts[1].strip() if len(parts) > 1 else ""
        new_title = t_map['lineup_title']
        new_body = t_map['lineup_body'].format(home=home, away=away)
        return new_title, new_body

    elif event_type == 'SCHEDULE':
        league = re.sub(r"\s+Schedule.*$", "", title, flags=re.IGNORECASE).strip()
        league = re.sub(r"^[📅\s]*", "", league).strip()
        m_body = re.search(r"(?:There are|Il y a|Morgen stehen|Ci son|Há|Yarın)\s*(\d+)\s*(?:matches|matchs|Spiele|partite|jogos|maç)", body, re.IGNORECASE)
        if m_body:
            count = m_body.group(1)
        else:
            count = "0"
        new_title = t_map['schedule_title'].format(league=league)
        new_body = t_map['schedule_body'].format(count=count, league=league)
        return new_title, new_body

    elif event_type == 'MATCH_START':
        m_body = re.search(r"(?:15 mins:|15 min:|15 minutos:|15 dakika içinde:|imminente)\s*(.+?)\s+(?:vs|-)\s+(.+)", body, re.IGNORECASE)
        if m_body:
            home, away = m_body.group(1).strip(), m_body.group(2).strip()
        else:
            clean_body = re.sub(r"^.*?(?:15 mins:|15 min:|15 minutos:|15 dakika içinde:)\s*", "", body, flags=re.IGNORECASE).strip()
            parts = re.split(r"\s+(?:vs|-)\s+", clean_body, flags=re.IGNORECASE)
            home = parts[0].strip() if len(parts) > 0 else ""
            away = parts[1].strip() if len(parts) > 1 else ""
        new_title = t_map['match_start_title']
        new_body = t_map['match_start_body'].format(home=home, away=away)
        return new_title, new_body

    elif event_type == 'CARD':
        is_red = '🟥' in title or 'Red' in title or 'second yellow' in title.lower()
        m_title = re.search(r"Card for\s+(.+?)\s+\((.+?)\)", title, re.IGNORECASE)
        player = m_title.group(1).strip() if m_title else ""
        team = m_title.group(2).strip() if m_title else ""
        
        m_body = re.search(r"in the\s+(\d+)|(\d+)'\s+minute|minute\s+(\d+)", body, re.IGNORECASE)
        time = ""
        if m_body:
            time = m_body.group(1) or m_body.group(2) or m_body.group(3)
        if not time:
            time_match = re.search(r"(\d+)", body)
            time = time_match.group(1) if time_match else ""

        key = 'card_red_title' if is_red else 'card_yellow_title'
        new_title = t_map[key].format(player=player, team=team)
        new_body = t_map['card_body'].format(player=player, time=time)
        return new_title, new_body

    elif event_type == 'SUBSTITUTION':
        m_title = re.search(r"for\s+(.+)$", title, re.IGNORECASE)
        team = m_title.group(1).strip() if m_title else ""
        
        m_body = re.search(r"In:\s*(.+?)\s*\|\s*Out:\s*(.+?)\s*\((.+?)\)", body, re.IGNORECASE)
        if m_body:
            player_in = m_body.group(1).strip()
            player_out = m_body.group(2).strip()
            time = m_body.group(3).replace("'", "").strip()
        else:
            player_in, player_out, time = "", "", ""
            
        new_title = t_map['sub_title'].format(team=team)
        new_body = t_map['sub_body'].format(player_in=player_in, player_out=player_out, time=time)
        return new_title, new_body

    elif event_type == 'VAR':
        m_title = re.search(r"Decision:\s*(.+)$", title, re.IGNORECASE)
        team = m_title.group(1).strip() if m_title else ""
        
        m_body = re.search(r"(.+?)\s*\((.+?)\)", body, re.IGNORECASE)
        if m_body:
            detail = m_body.group(1).strip()
            time = m_body.group(2).replace("'", "").strip()
        else:
            detail = body
            time = ""
            
        new_title = t_map['var_title'].format(team=team)
        new_body = t_map['var_body'].format(detail=detail, time=time)
        return new_title, new_body

    return title, body

def update_device_topic_subscriptions(device, old_lang, new_lang):
    if old_lang == new_lang:
        return
    
    NotificationService.ensure_firebase_initialized()
    
    team_ids = []
    league_ids = []
    fixture_ids = []
    
    if device.user:
        if hasattr(device.user, 'fan_profile'):
            profile = device.user.fan_profile
            team_ids = list(profile.favorite_teams.values_list('id', flat=True))
            league_ids = list(profile.favorite_leagues.values_list('id', flat=True))
            fixture_ids = list(profile.favorite_fixtures.values_list('id', flat=True))
    elif device.guest_id:
        from users.models import GuestFavorite
        fav = GuestFavorite.objects.filter(device_id=device.guest_id).first()
        if fav:
            team_ids = list(fav.favorite_teams.values_list('id', flat=True))
            league_ids = list(fav.favorite_leagues.values_list('id', flat=True))
            fixture_ids = list(fav.favorite_fixtures.values_list('id', flat=True))
            
    # Unsubscribe from old language topics
    old_topics = (
        [f"team_{tid}_{old_lang}" for tid in team_ids] + 
        [f"league_{lid}_{old_lang}" for lid in league_ids] +
        [f"match_{fid}_{old_lang}" for fid in fixture_ids] +
        [f"fixture_{fid}_{old_lang}" for fid in fixture_ids] +
        [f"global_{old_lang}"]
    )
    for topic in old_topics:
        try:
            messaging.unsubscribe_from_topic([device.registration_id], topic)
            print(f"Language migration: unsubscribed {device.registration_id} from {topic}")
        except Exception as e:
            print(f"Error unsubscribing {device.registration_id} from {topic}: {e}")
            
    # Subscribe to new language topics
    new_topics = (
        [f"team_{tid}_{new_lang}" for tid in team_ids] + 
        [f"league_{lid}_{new_lang}" for lid in league_ids] +
        [f"match_{fid}_{new_lang}" for fid in fixture_ids] +
        [f"fixture_{fid}_{new_lang}" for fid in fixture_ids] +
        [f"global_{new_lang}"]
    )
    for topic in new_topics:
        try:
            messaging.subscribe_to_topic([device.registration_id], topic)
            print(f"Language migration: subscribed {device.registration_id} to {topic}")
        except Exception as e:
            print(f"Error subscribing {device.registration_id} to {topic}: {e}")

def sync_device_subscriptions(device):
    """
    Subscribes a device registration token to all fanned-out topics of its owner's favorites.
    Called when a device token is registered or updated.
    """
    NotificationService.ensure_firebase_initialized()
    user = device.user
    guest_id = device.guest_id
    lang = device.language or 'en'
    
    team_ids = []
    league_ids = []
    fixture_ids = []
    
    if user:
        if hasattr(user, 'fan_profile'):
            profile = user.fan_profile
            team_ids = list(profile.favorite_teams.values_list('id', flat=True))
            league_ids = list(profile.favorite_leagues.values_list('id', flat=True))
            fixture_ids = list(profile.favorite_fixtures.values_list('id', flat=True))
    elif guest_id:
        from users.models import GuestFavorite
        fav = GuestFavorite.objects.filter(device_id=guest_id).first()
        if fav:
            team_ids = list(fav.favorite_teams.values_list('id', flat=True))
            league_ids = list(fav.favorite_leagues.values_list('id', flat=True))
            fixture_ids = list(fav.favorite_fixtures.values_list('id', flat=True))
            
    # Subscribe to team topics in device's preferred language
    for tid in team_ids:
        try:
            NotificationService.subscribe_tokens_to_topic([device.registration_id], f"team_{tid}_{lang}")
        except Exception as e:
            print(f"Failed to subscribe device {device.id} to team_{tid}_{lang}: {e}")
            
    # Subscribe to league topics in device's preferred language
    for lid in league_ids:
        try:
            NotificationService.subscribe_tokens_to_topic([device.registration_id], f"league_{lid}_{lang}")
        except Exception as e:
            print(f"Failed to subscribe device {device.id} to league_{lid}_{lang}: {e}")
            
    # Subscribe to fixture/match topics in device's preferred language
    for fid in fixture_ids:
        try:
            NotificationService.subscribe_tokens_to_topic([device.registration_id], f"match_{fid}_{lang}")
            NotificationService.subscribe_tokens_to_topic([device.registration_id], f"fixture_{fid}_{lang}")
        except Exception as e:
            print(f"Failed to subscribe device {device.id} to match/fixture {fid}_{lang}: {e}")

    # Subscribe to global topic in device's preferred language
    try:
        NotificationService.subscribe_tokens_to_topic([device.registration_id], f"global_{lang}")
    except Exception as e:
        print(f"Failed to subscribe device {device.id} to global_{lang}: {e}")


class NotificationService:
    @staticmethod
    def ensure_firebase_initialized():
        """
        Lazily initialize Firebase Admin SDK.
        Ensures Celery workers never fail silently if apps.py couldn't initialize.
        """
        if not firebase_admin._apps:
            if getattr(settings, 'FIREBASE_CONFIGURED', False):
                try:
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    firebase_admin.initialize_app(cred)
                    print("Firebase Admin lazily initialized in NotificationService.")
                except Exception as e:
                    print(f"CRITICAL: Failed to initialize Firebase in NotificationService: {e}")
                    # Log if the file is a directory (Docker volume common issue) or missing
                    if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                        print("ERROR: firebase-credentials.json is COMPLETELY MISSING!")
                    elif os.path.isdir(settings.FIREBASE_CREDENTIALS_PATH):
                        print("ERROR: firebase-credentials.json is a DIRECTORY, not a file!")
                    else:
                        try:
                            with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                                content = f.read()
                                print(f"\n{'='*60}")
                                print(f"📄 FIREBASE JSON CONTENTS MOUNTED IN DOCKER:")
                                print(content)
                                print(f"{'='*60}\n")
                        except Exception as read_err:
                            print(f"Could not read the file for debugging: {read_err}")
            else:
                print("Firebase Admin SDK is in Simulator Mode (missing or placeholder credentials). Skipping initialization.")

    @staticmethod
    def send_push_to_topic(topic, title, body, data=None, event_type='CUSTOM', is_internal=False):
        """
        Sends a message to a topic and logs it with the specific event type.
        Supports language-specific topic fan-out and user-specific translations.
        """
        # Ensure data is dict and make a copy to avoid mutating the caller's dictionary
        data = data.copy() if data is not None else {}
        
        # Enforce click_action
        if "click_action" not in data:
            data["click_action"] = "FLUTTER_NOTIFICATION_CLICK"
            
        # Map event_type to routing type if type is missing or incorrect
        if "type" not in data:
            if event_type in ['GOAL', 'FULL_TIME', 'LINEUPS', 'MATCH_START', 'CARD', 'SUBSTITUTION', 'VAR']:
                data["type"] = "match"
            elif event_type in ['SCHEDULE', 'LEAGUE_UPDATE']:
                data["type"] = "league"
            elif event_type in ['TEAM_NEWS']:
                data["type"] = "team"
            elif event_type in ['PLAYER_UPDATE']:
                data["type"] = "player"
            else:
                data["type"] = "general"
                
        # Ensure event_type is in data for the mobile app
        if "event_type" not in data:
            data["event_type"] = event_type
            
        # 1. Topic Fanout for base sports/global topics
        if not is_internal and (topic.startswith("team_") or topic.startswith("league_") or topic.startswith("match_") or topic.startswith("fixture_") or topic == "global"):
            # Create a single base notification log for user's personal inboxes
            try:
                NotificationLog.objects.create(
                    topic=topic,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type=event_type,
                    error_message="Base sports topic logged for inbox. Fanned out to language topics.",
                    data=data
                )
            except Exception as e:
                print(f"Database logging failed for base topic {topic}: {e}")

            # Fan out to all supported languages
            for lang in ['en', 'es', 'fr', 'de', 'it', 'pt', 'tr']:
                t_title, t_body = translate_notification(title, body, event_type, lang)
                NotificationService.send_push_to_topic(
                    f"{topic}_{lang}", t_title, t_body, data, event_type, is_internal=True
                )
            return True

        # 2. Translate user-specific notifications based on their profile language
        if not is_internal and topic.startswith("user_"):
            lang = 'en'
            try:
                user_id = topic.split('_')[1]
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                if hasattr(user, 'fan_profile'):
                    lang = user.fan_profile.language
            except Exception:
                pass
            title, body = translate_notification(title, body, event_type, lang)

        # Check if we should use Simulated Dev Mode
        use_simulator = not getattr(settings, 'FIREBASE_CONFIGURED', False)
        
        if use_simulator:
            print(f"\n{'='*60}")
            print(f"⚠️  SIMULATOR MODE: FIREBASE CREDENTIALS MISSING OR PLACEHOLDER")
            print(f"   Simulating Push to Topic: {topic}")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {data}")
            print(f"{'='*60}\n")
            
            # For user-specific or custom topics (not fanned out base topics), log to DB
            if topic.startswith("user_") or (not topic.startswith("team_") and not topic.startswith("league_") and not topic.startswith("match_") and not topic.startswith("fixture_") and topic != "global" and not is_internal):
                try:
                    NotificationLog.objects.create(
                        topic=topic,
                        title=title,
                        body=body,
                        status='SENT',
                        event_type=event_type,
                        error_message="[SIMULATED] User or custom topic.",
                        data=data
                    )
                except Exception as e:
                    print(f"Database logging failed: {e}")
            return True

        # Otherwise, proceed with actual Firebase sending
        NotificationService.ensure_firebase_initialized()
        
        status = 'SENT'
        error_msg = None
        
        # Determine deduplication collapse key / APNS collapse ID
        collapse_key = None
        if data and "match_id" in data:
            match_id = data["match_id"]
            if event_type == 'FULL_TIME':
                collapse_key = f"match_{match_id}_ft"
            elif event_type == 'GOAL':
                score = str(data.get("score", "goal")).replace(" ", "")
                collapse_key = f"match_{match_id}_goal_{score}"
            elif event_type == 'LINEUPS':
                collapse_key = f"match_{match_id}_lineups"
            elif event_type == 'MATCH_START':
                collapse_key = f"match_{match_id}_kickoff"

        android_config = None
        apns_config = None

        # Build APNS configuration payload for iOS devices (sound, alert, badge, background delivery)
        apns_headers = {
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        if collapse_key:
            apns_headers["apns-collapse-id"] = collapse_key

        apns_config = messaging.APNSConfig(
            headers=apns_headers,
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound="default",
                    badge=1,
                    content_available=True,
                    mutable_content=True,
                )
            )
        )

        if collapse_key:
            android_config = messaging.AndroidConfig(
                collapse_key=collapse_key
            )

        try:
            # Firebase only accepts strings in data map
            formatted_data = {k: str(v) for k, v in data.items()}
            
            print(f"\n{'='*60}")
            print(f"🚀 PUSHING TO FIREBASE TOPIC: {topic}")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {formatted_data}")
            print(f"   Collapse Key: {collapse_key}")
            print(f"{'='*60}\n")
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=formatted_data,
                topic=topic,
                android=android_config,
                apns=apns_config,
            )
            response = messaging.send(message=message)
            error_msg = str(response) # Save Firebase Message ID to DB
            
            print(f"\n{'='*60}")
            print(f"✅ SUCCESS! FIREBASE ACCEPTED NOTIFICATION")
            print(f"   Message ID: {response}")
            print(f"   Topic: {topic}")
            print(f"{'='*60}\n")
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            print(f"Push Error ({topic}): {e}")
            
            # --- USER DEMAND: PROOF OF JSON FILE ---
            try:
                with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                    print(f"\n{'='*60}")
                    print(f"📄 FIREBASE JSON FILE AS SEEN BY DOCKER (Proof):")
                    print(f.read())
                    print(f"{'='*60}\n")
            except Exception as read_err:
                print(f"Could not read the file for debugging: {read_err}")
        
        # Log to DB only for user topics or custom non-fanned-out topics to avoid duplicates
        if topic.startswith("user_") or (not topic.startswith("team_") and not topic.startswith("league_") and not topic.startswith("match_") and not topic.startswith("fixture_") and topic != "global" and not is_internal):
            try:
                NotificationLog.objects.create(
                    topic=topic,
                    title=title,
                    body=body,
                    status=status,
                    event_type=event_type,
                    error_message=error_msg,
                    data=data
                )
            except Exception:
                pass
        return status == 'SENT'
    
    @staticmethod
    def send_push_to_token(token, title, body, data=None):
        """
        TEMPORARY: Sends a message directly to a specific device FCM token for testing.
        If firebase credentials are missing, falls back to simulated sent state for dev/testing.
        """
        # Ensure data is dict and make a copy to avoid mutating the caller's dictionary
        data = data.copy() if data is not None else {}
        
        # Enforce click_action
        if "click_action" not in data:
            data["click_action"] = "FLUTTER_NOTIFICATION_CLICK"
            
        # Extract event_type from data if present, otherwise default to DEV_TEST
        evt_type = data.get("event_type") or data.get("type") or "DEV_TEST"
        
        # Enforce routing type if missing
        if "type" not in data:
            if evt_type in ['GOAL', 'FULL_TIME', 'LINEUPS', 'MATCH_START', 'match']:
                data["type"] = "match"
            elif evt_type in ['SCHEDULE', 'LEAGUE_UPDATE', 'league']:
                data["type"] = "league"
            elif evt_type in ['TEAM_NEWS', 'team']:
                data["type"] = "team"
            elif evt_type in ['PLAYER_UPDATE', 'player']:
                data["type"] = "player"
            else:
                data["type"] = "general"
                
        # Ensure event_type is present in data
        if "event_type" not in data:
            data["event_type"] = evt_type
        
        use_simulator = not getattr(settings, 'FIREBASE_CONFIGURED', False)
        
        # Determine inbox topic to associate the notification log with the user or guest inbox
        db_topic = f"token_{token[:20]}"
        try:
            from .models import UserDevice
            device = UserDevice.objects.filter(registration_id=token).first()
            if device:
                if device.user:
                    db_topic = f"user_{device.user.id}"
                elif device.guest_id:
                    db_topic = f"guest_{device.guest_id}"
        except Exception:
            pass

        if use_simulator:
            print(f"\n{'='*60}")
            print(f"⚠️  SIMULATOR MODE: FIREBASE CREDENTIALS MISSING OR PLACEHOLDER")
            print(f"   Simulating Push to Token: {token[:20]}...")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {data}")
            print(f"{'='*60}\n")
            
            try:
                NotificationLog.objects.create(
                    topic=db_topic,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type=evt_type,
                    error_message="[SIMULATED] Firebase credentials missing, simulated successfully.",
                    data=data
                )
            except Exception as e:
                print(f"Database logging failed: {e}")
                
            return {"success": True, "message_id": "simulated-msg-id-12345", "simulated": True}

        # Otherwise proceed with actual Firebase sending
        NotificationService.ensure_firebase_initialized()
        formatted_data = {k: str(v) for k, v in data.items()}
        
        # Determine deduplication collapse key / APNS collapse ID
        collapse_key = None
        if data and "match_id" in data:
            match_id = data["match_id"]
            if evt_type == 'FULL_TIME':
                collapse_key = f"match_{match_id}_ft"
            elif evt_type == 'GOAL':
                score = str(data.get("score", "goal")).replace(" ", "")
                collapse_key = f"match_{match_id}_goal_{score}"
            elif evt_type == 'LINEUPS':
                collapse_key = f"match_{match_id}_lineups"
            elif evt_type == 'MATCH_START':
                collapse_key = f"match_{match_id}_kickoff"

        android_config = None
        apns_config = None

        # Build APNS configuration payload for iOS devices (sound, alert, badge, background delivery)
        apns_headers = {
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        if collapse_key:
            apns_headers["apns-collapse-id"] = collapse_key

        apns_config = messaging.APNSConfig(
            headers=apns_headers,
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound="default",
                    badge=1,
                    content_available=True,
                    mutable_content=True,
                )
            )
        )

        if collapse_key:
            android_config = messaging.AndroidConfig(
                collapse_key=collapse_key
            )

        print(f"\n{'='*60}")
        print(f"🚀 PUSHING TO FIREBASE TOKEN: {token[:20]}...")
        print(f"   Title: {title}")
        print(f"   Body: {body}")
        print(f"   Collapse Key: {collapse_key}")
        print(f"{'='*60}\n")
        
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=formatted_data,
            token=token,
            android=android_config,
            apns=apns_config,
        )
        try:
            response = messaging.send(message=message)
            print(f"✅ SUCCESS! FIREBASE ACCEPTED TOKEN NOTIFICATION: {response}")
            
            try:
                NotificationLog.objects.create(
                    topic=db_topic,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type=evt_type,
                    error_message=str(response),
                    data=data
                )
            except Exception:
                pass
                
            return {"success": True, "message_id": response}
        except Exception as e:
            print(f"❌ Failed to send to token: {e}")
            
            try:
                NotificationLog.objects.create(
                    topic=db_topic,
                    title=title,
                    body=body,
                    status='FAILED',
                    event_type=evt_type,
                    error_message=str(e),
                    data=data
                )
            except Exception:
                pass
                
            try:
                with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                    pass # Silenced to not clutter logs anymore
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_goal_alert(scoring_team_name, home_team_name, away_team_name, score, home_team_id, away_team_id, match_id, league_id=None):
        """
        Sends goal alerts to Team Topics, Match Topic, and optionally League Topic.
        """
        title = f"⚽ Goal by {scoring_team_name}!"
        body = f"Current Score: {home_team_name} {score} {away_team_name}"
                # 1. Send to Home Team Fans
        data_home = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "GOAL",
            "match_id": str(match_id), 
            "team_id": str(home_team_id),
            "score": str(score),
            "reason": f"Following {home_team_name}"
        }
        NotificationService.send_push_to_topic(f"team_{home_team_id}", title, body, data_home, event_type='GOAL')
        
        # 2. Send to Away Team Fans
        data_away = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "GOAL",
            "match_id": str(match_id), 
            "team_id": str(away_team_id),
            "score": str(score),
            "reason": f"Following {away_team_name}"
        }
        NotificationService.send_push_to_topic(f"team_{away_team_id}", title, body, data_away, event_type='GOAL')
        
        # 3. Send to Match Followers
        data_match = data_home.copy()
        data_match["reason"] = f"Saved Match"
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, event_type='GOAL')

        # 4. Send to League Followers (if provided)
        if league_id:
            data_league = data_home.copy()
            data_league["reason"] = "Following League"
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, event_type='GOAL')

    @staticmethod
    def send_match_result_alert(home_team, away_team, score, match_id, league_id):
        """
        Sends Full Time results to BOTH teams, the Match Topic, AND the League Topic.
        """
        title = "🏁 Full Time"
        body = f"Final Result: {home_team.name} {score} {away_team.name}"
        
        # 1. Send to Home Team Fans
        data_home = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "FULL_TIME",
            "match_id": str(match_id),
            "reason": f"Following {home_team.name}"
        }
        NotificationService.send_push_to_topic(f"team_{home_team.id}", title, body, data_home, 'FULL_TIME')
        
        # 2. Send to Away Team Fans
        data_away = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "FULL_TIME",
            "match_id": str(match_id),
            "reason": f"Following {away_team.name}"
        }
        NotificationService.send_push_to_topic(f"team_{away_team.id}", title, body, data_away, 'FULL_TIME')
        
        # 3. Send to Match Followers
        data_match = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "FULL_TIME",
            "match_id": str(match_id),
            "reason": "Saved Match"
        }
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, 'FULL_TIME')

        # 4. Send to League Followers
        data_league = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "FULL_TIME",
            "match_id": str(match_id),
            "reason": "Following League"
        }
        NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, 'FULL_TIME')
    
    @staticmethod
    def send_lineup_alert(home_team, away_team, match_id, league_id=None):
        """
        Sends Lineup Confirmation to Team Topics, Match Topic, and League Topic.
        """
        title = "📋 Lineups Released"
        body = f"Starting XI is now available for {home_team.name} vs {away_team.name}"
        data_home = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "LINEUPS",
            "match_id": str(match_id),
            "reason": f"Following {home_team.name}"
        }
        NotificationService.send_push_to_topic(f"team_{home_team.id}", title, body, data_home, 'LINEUPS')

        data_away = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "LINEUPS",
            "match_id": str(match_id),
            "reason": f"Following {away_team.name}"
        }
        NotificationService.send_push_to_topic(f"team_{away_team.id}", title, body, data_away, 'LINEUPS')
        
        data_match = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "LINEUPS",
            "match_id": str(match_id),
            "reason": "Saved Match"
        }
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, 'LINEUPS')

        if league_id:
            data_league = {
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "type": "match",
                "event_type": "LINEUPS",
                "match_id": str(match_id),
                "reason": "Following League"
            }
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, 'LINEUPS')
    
    @staticmethod
    def send_league_daily_update(league_name, match_count, league_id):
        """
        Sends a daily schedule summary for a league.
        """
        title = f"📅 {league_name} Schedule"
        body = f"There are {match_count} matches starting tomorrow in {league_name}. Don't miss out!"
        data = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "league",
            "event_type": "SCHEDULE",
            "league_id": str(league_id),
            "reason": f"Following {league_name}"
        }
        NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data, 'SCHEDULE')

    @staticmethod
    def send_card_alert(player_name, card_type, team_name, team_id, match_id, elapsed_time, league_id=None):
        """
        Sends Card alerts (Yellow, Red, etc.) to Team Topics, Match Topic, and optionally League Topic.
        """
        card_emoji = "🟥" if "Red" in card_type or "Second" in card_type else "🟨"
        title = f"{card_emoji} Card for {player_name} ({team_name})"
        body = f"{player_name} received a {card_type} in the {elapsed_time}' minute."
        
        data_match = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "CARD",
            "match_id": str(match_id),
            "team_id": str(team_id),
            "player_name": player_name,
            "card_type": card_type,
            "elapsed": str(elapsed_time),
            "reason": "Saved Match"
        }
        
        # 1. Send to Match Followers
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, event_type='CARD')
        
        # 2. Send to Team Followers
        data_team = data_match.copy()
        data_team["reason"] = f"Following {team_name}"
        NotificationService.send_push_to_topic(f"team_{team_id}", title, body, data_team, event_type='CARD')
        
        # 3. Send to League Followers (if provided)
        if league_id:
            data_league = data_match.copy()
            data_league["reason"] = "Following League"
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, event_type='CARD')

    @staticmethod
    def send_substitution_alert(player_in, player_out, team_name, team_id, match_id, elapsed_time, league_id=None):
        """
        Sends Substitution alerts to Team Topics, Match Topic, and optionally League Topic.
        """
        title = f"🔄 Substitution for {team_name}"
        body = f"In: {player_in} | Out: {player_out} ({elapsed_time}')"
        
        data_match = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "SUBSTITUTION",
            "match_id": str(match_id),
            "team_id": str(team_id),
            "player_in": player_in,
            "player_out": player_out,
            "elapsed": str(elapsed_time),
            "reason": "Saved Match"
        }
        
        # 1. Send to Match Followers
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, event_type='SUBSTITUTION')
        
        # 2. Send to Team Followers
        data_team = data_match.copy()
        data_team["reason"] = f"Following {team_name}"
        NotificationService.send_push_to_topic(f"team_{team_id}", title, body, data_team, event_type='SUBSTITUTION')
        
        # 3. Send to League Followers (if provided)
        if league_id:
            data_league = data_match.copy()
            data_league["reason"] = "Following League"
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, event_type='SUBSTITUTION')

    @staticmethod
    def send_var_alert(detail, team_name, team_id, match_id, elapsed_time, league_id=None):
        """
        Sends VAR decision alerts to Team Topics, Match Topic, and optionally League Topic.
        """
        title = f"🖥️ VAR Decision: {team_name}"
        body = f"{detail} ({elapsed_time}')"
        
        data_match = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "match",
            "event_type": "VAR",
            "match_id": str(match_id),
            "team_id": str(team_id),
            "detail": detail,
            "elapsed": str(elapsed_time),
            "reason": "Saved Match"
        }
        
        # 1. Send to Match Followers
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, event_type='VAR')
        
        # 2. Send to Team Followers
        data_team = data_match.copy()
        data_team["reason"] = f"Following {team_name}"
        NotificationService.send_push_to_topic(f"team_{team_id}", title, body, data_team, event_type='VAR')
        
        # 3. Send to League Followers (if provided)
        if league_id:
            data_league = data_match.copy()
            data_league["reason"] = "Following League"
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, event_type='VAR')

    # --- Subscription Helpers ---
    @staticmethod
    def subscribe_tokens_to_topic(tokens, topic):
        NotificationService.ensure_firebase_initialized()
        if not tokens: return
        
        supported_langs = ['en', 'es', 'fr', 'de', 'it', 'pt', 'tr']
        has_lang_suffix = any(topic.endswith(f"_{l}") for l in supported_langs)
        
        if has_lang_suffix:
            batch_size = 1000
            for i in range(0, len(tokens), batch_size):
                batch = tokens[i:i + batch_size]
                try:
                    messaging.subscribe_to_topic(batch, topic)
                    print(f"Subscribed {len(batch)} tokens to {topic}")
                except Exception as e:
                    print(f"Error subscribing to {topic}: {e}")
            return
        
        # Determine language for each token
        from .models import UserDevice
        devices = UserDevice.objects.filter(registration_id__in=tokens)
        token_to_lang = {d.registration_id: d.language for d in devices}
        
        # Group tokens by language
        lang_groups = {}
        for token in tokens:
            lang = token_to_lang.get(token, 'en')
            lang_groups.setdefault(lang, []).append(token)
            
        for lang, lang_tokens in lang_groups.items():
            lang_topic = f"{topic}_{lang}"
            batch_size = 1000
            for i in range(0, len(lang_tokens), batch_size):
                batch = lang_tokens[i:i + batch_size]
                try:
                    messaging.subscribe_to_topic(batch, lang_topic)
                    print(f"Subscribed {len(batch)} tokens to {lang_topic}")
                except Exception as e:
                    print(f"Error subscribing to {lang_topic}: {e}")

    @staticmethod
    def unsubscribe_tokens_from_topic(tokens, topic):
        NotificationService.ensure_firebase_initialized()
        if not tokens: return
        
        supported_langs = ['en', 'es', 'fr', 'de', 'it', 'pt', 'tr']
        has_lang_suffix = any(topic.endswith(f"_{l}") for l in supported_langs)
        
        if has_lang_suffix:
            batch_size = 1000
            for i in range(0, len(tokens), batch_size):
                batch = tokens[i:i + batch_size]
                try:
                    messaging.unsubscribe_from_topic(batch, topic)
                    print(f"Unsubscribed {len(batch)} tokens from {topic}")
                except Exception as e:
                    print(f"Error unsubscribing from {topic}: {e}")
            return
        
        # Determine language for each token
        from .models import UserDevice
        devices = UserDevice.objects.filter(registration_id__in=tokens)
        token_to_lang = {d.registration_id: d.language for d in devices}
        
        # Group tokens by language
        lang_groups = {}
        for token in tokens:
            lang = token_to_lang.get(token, 'en')
            lang_groups.setdefault(lang, []).append(token)
            
        for lang, lang_tokens in lang_groups.items():
            lang_topic = f"{topic}_{lang}"
            batch_size = 1000
            for i in range(0, len(lang_tokens), batch_size):
                batch = lang_tokens[i:i + batch_size]
                try:
                    messaging.unsubscribe_from_topic(batch, lang_topic)
                    print(f"Unsubscribed {len(batch)} tokens from {lang_topic}")
                except Exception as e:
                    print(f"Error unsubscribing from {lang_topic}: {e}")