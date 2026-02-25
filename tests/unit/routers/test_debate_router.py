from app.models.debate import (
    DEFAULT_PERSONA_A,
    DEFAULT_PERSONA_B,
    Persona,
    PersonaInput,
)
from app.routers.debate import _to_persona


class TestToPersona:
    def test_名前と説明が両方入力済みならそのまま返す(self) -> None:
        # Given
        inp = PersonaInput(name="楽観派", description="明るく前向きな立場")
        default = DEFAULT_PERSONA_A

        # When
        result = _to_persona(inp, default)

        # Then
        assert result.name == "楽観派"
        assert result.description == "明るく前向きな立場"

    def test_名前が空ならデフォルト名を使用する(self) -> None:
        # Given
        inp = PersonaInput(name="", description="説明あり")
        default = DEFAULT_PERSONA_A

        # When
        result = _to_persona(inp, default)

        # Then
        assert result.name == DEFAULT_PERSONA_A.name
        assert result.description == "説明あり"

    def test_説明が空ならデフォルト説明を使用する(self) -> None:
        # Given
        inp = PersonaInput(name="名前あり", description="")
        default = DEFAULT_PERSONA_B

        # When
        result = _to_persona(inp, default)

        # Then
        assert result.name == "名前あり"
        assert result.description == DEFAULT_PERSONA_B.description

    def test_両方空ならデフォルトを両方使用する(self) -> None:
        # Given
        inp = PersonaInput(name="", description="")
        default = DEFAULT_PERSONA_A

        # When
        result = _to_persona(inp, default)

        # Then
        assert result.name == DEFAULT_PERSONA_A.name
        assert result.description == DEFAULT_PERSONA_A.description

    def test_空白のみの名前はデフォルトにフォールバックする(self) -> None:
        # Given: strip後に空になる
        inp = PersonaInput(name="   ", description="   ")
        default = DEFAULT_PERSONA_B

        # When
        result = _to_persona(inp, default)

        # Then
        assert result.name == DEFAULT_PERSONA_B.name
        assert result.description == DEFAULT_PERSONA_B.description

    def test_非対称_名前のみ入力の場合(self) -> None:
        # Given: persona_aのデフォルトとpersona_bのデフォルトが異なることを確認
        inp_a = PersonaInput(name="", description="")
        inp_b = PersonaInput(name="", description="")

        # When
        result_a = _to_persona(inp_a, DEFAULT_PERSONA_A)
        result_b = _to_persona(inp_b, DEFAULT_PERSONA_B)

        # Then: 各ペルソナで異なるデフォルトが適用される
        assert result_a.name == DEFAULT_PERSONA_A.name  # 賛成派
        assert result_b.name == DEFAULT_PERSONA_B.name  # 反対派
        assert result_a.name != result_b.name

    def test_戻り値の型はPersona(self) -> None:
        # Given
        inp = PersonaInput(name="テスト", description="説明")
        default = DEFAULT_PERSONA_A

        # When
        result = _to_persona(inp, default)

        # Then
        assert isinstance(result, Persona)
