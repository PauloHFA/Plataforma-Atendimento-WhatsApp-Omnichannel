from src.flows.csat import CSATService
from src.privacy.masking import mask_cpf, mask_phone, mask_text


def test_mask_phone() -> None:
    assert mask_phone("5511999998888") == "55****8888"
    assert mask_phone("+55 (11) 98765-4321") == "55****4321"
    assert mask_phone("123") == "****"


def test_mask_cpf() -> None:
    assert mask_cpf("123.456.789-00") == "***.***.789-**"
    assert mask_cpf("12345678900") == "***.***.789-**"
    assert mask_cpf("123") == "***.***.***-**"


def test_mask_text() -> None:
    text = "Meu telefone é +55 11 99999-8888 e meu CPF é 123.456.789-00."
    masked = mask_text(text)
    assert "123.456.789-00" not in masked
    assert "***.***.***-**" in masked or "***.***.789-**" in masked
    assert "99999-8888" not in masked


def test_csat_service() -> None:
    csat = CSATService()
    assert csat.extract_score("5") == 5
    assert csat.extract_score("Eu dou nota 4!") == 4
    assert csat.extract_score("Nota 1, muito ruim") == 1
    assert csat.extract_score("Nota 10") is None
    assert csat.extract_score("nenhuma nota") is None
