from src.nlu.intent_classifier import IntentClassifier


def test_intent_classifier_greetings() -> None:
    clf = IntentClassifier()
    for text in ["Olá", "oi!", "Bom dia", "BOA TARDE"]:
        res = clf.classify(text)
        assert res.intent == "greeting"
        assert res.confidence >= 0.9


def test_intent_classifier_opt_out() -> None:
    clf = IntentClassifier()
    for text in ["PARAR", "Quero sair", "cancelar", "descadastrar"]:
        res = clf.classify(text)
        assert res.intent == "opt_out"
        assert res.confidence == 1.0


def test_intent_classifier_human_agent() -> None:
    clf = IntentClassifier()
    for text in ["Quero falar com um atendente", "humano por favor", "preciso de suporte"]:
        res = clf.classify(text)
        assert res.intent == "human_agent"
        assert res.confidence >= 0.95


def test_intent_classifier_order_status() -> None:
    clf = IntentClassifier()
    res = clf.classify("Gostaria de rastrear o pedido 123456")
    assert res.intent == "order_status"
    assert res.entities.get("order_number") == "123456"

    res2 = clf.classify("onde está meu pedido #ABC89")
    assert res2.intent == "order_status"
    assert res2.entities.get("order_number") == "ABC89"


def test_intent_classifier_appointment() -> None:
    clf = IntentClassifier()
    for text in ["Gostaria de agendar uma consulta", "marcar horario", "remarcar"]:
        res = clf.classify(text)
        assert res.intent == "appointment"
        assert res.confidence >= 0.9


def test_intent_classifier_unrecognized() -> None:
    clf = IntentClassifier()
    res = clf.classify("xyz123 aleatorio qualquer")
    assert res.intent == "unrecognized"
    assert res.confidence <= 0.5
