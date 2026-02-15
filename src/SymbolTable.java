import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public final class SymbolTable {
    public static final class SymbolEntry {
        private final String name;
        private final String type;
        private final int firstLine;
        private final int firstColumn;
        private int frequency;

        private SymbolEntry(String name, String type, int firstLine, int firstColumn) {
            this.name = name;
            this.type = type;
            this.firstLine = firstLine;
            this.firstColumn = firstColumn;
            this.frequency = 1;
        }

        public String getName() {
            return name;
        }

        public String getType() {
            return type;
        }

        public int getFirstLine() {
            return firstLine;
        }

        public int getFirstColumn() {
            return firstColumn;
        }

        public int getFrequency() {
            return frequency;
        }

        private void incrementFrequency() {
            frequency++;
        }
    }

    private final Map<String, SymbolEntry> entries = new LinkedHashMap<>();

    public void recordIdentifier(String identifier, int line, int column) {
        SymbolEntry entry = entries.get(identifier);
        if (entry == null) {
            entries.put(identifier, new SymbolEntry(identifier, "identifier", line, column));
            return;
        }
        entry.incrementFrequency();
    }

    public Collection<SymbolEntry> getEntries() {
        return Collections.unmodifiableCollection(entries.values());
    }

    public void print() {
        System.out.println("Symbol Table:");
        if (entries.isEmpty()) {
            System.out.println("  (empty)");
            return;
        }
        System.out.println("  Name | Type | First Occurrence | Frequency");
        for (SymbolEntry entry : entries.values()) {
            String first = "Line " + entry.getFirstLine() + ", Col " + entry.getFirstColumn();
            System.out.println(
                "  " + entry.getName()
                    + " | " + entry.getType()
                    + " | " + first
                    + " | " + entry.getFrequency()
            );
        }
    }
}
