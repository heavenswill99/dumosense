def answer_chat_message(message):
    text = message.casefold()

    if any(
        phrase in text
        for phrase in (
            "suicide",
            "kill myself",
            "hurt myself",
            "self-harm",
            "can't breathe",
            "chest pain",
            "emergency",
        )
    ):
        return (
            "If you may be in immediate danger or might hurt yourself, contact "
            "your local emergency services now. If possible, reach someone you "
            "trust. I can't provide emergency care."
        )

    if any(
        term in text
        for term in ("diagnose", "diagnosis", "treatment", "medication", "prescribe")
    ):
        return (
            "I can't diagnose conditions or recommend treatment or medication. "
            "A qualified healthcare professional can discuss your symptoms and "
            "options with you."
        )

    if any(term in text for term in ("my pattern", "my results", "my data", "my records")):
        return (
            "I can't access or interpret your personal check-in records in this "
            "chat. I can explain how to use MindGuard or Health Reserve, but I "
            "won't provide a personal health assessment."
        )

    if any(term in text for term in ("mindguard", "check-in", "check in")):
        return (
            "MindGuard is where you can record personal wellbeing and cognitive "
            "reflections over time. Choose the options that best describe your "
            "experience; the check-in is not a diagnosis or clinical test."
        )

    if any(term in text for term in ("health reserve", "preparedness", "reserve")):
        return (
            "Health Reserve is a planning tool for thinking about possible "
            "health-related costs and preparedness. Its estimates are for "
            "reflection only, not financial advice."
        )

    if any(term in text for term in ("privacy", "personal information", "data")):
        return (
            "This chat is handled by the Dumosense backend and does not use an "
            "external AI service or read your saved health records. Avoid "
            "including sensitive personal information in messages."
        )

    if any(term in text for term in ("stress", "anxious", "anxiety", "mood", "overwhelmed")):
        return (
            "If it feels useful, take a short pause, try a few slow breaths, or "
            "talk with someone you trust. If these feelings persist or are "
            "affecting daily life, consider speaking with a qualified "
            "professional."
        )

    if any(term in text for term in ("sleep", "tired", "rest")):
        return (
            "A steady wind-down routine and a comfortable, quiet sleep "
            "environment may help. If sleep difficulties continue or concern "
            "you, a healthcare professional can offer guidance."
        )

    return (
        "I can explain Dumosense features and share general wellbeing "
        "information. I don't access your personal health records, diagnose, "
        "or give medical or financial advice. What would you like to know?"
    )
