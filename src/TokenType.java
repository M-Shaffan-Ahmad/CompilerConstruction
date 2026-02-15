public enum TokenType {
    SINGLE_LINE_COMMENT("SINGLE_LINE_COMMENT"),
    BOOLEAN_LITERAL("BOOLEAN_LITERAL"),
    IDENTIFIER("IDENTIFIER"),
    FLOATING_POINT_LITERAL("FLOATING_POINT_LITERAL"),
    INTEGER_LITERAL("INTEGER_LITERAL"),
    SINGLE_CHAR_OPERATOR("SINGLE_CHAR_OPERATOR"),
    PUNCTUATOR("PUNCTUATOR");

    private final String label;

    TokenType(String label) {
        this.label = label;
    }

    @Override
    public String toString() {
        return label;
    }
}
