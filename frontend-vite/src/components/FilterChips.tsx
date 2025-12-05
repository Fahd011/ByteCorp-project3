import { useState } from "react";
import { ChevronRight } from "lucide-react";

interface FilterChipsProps {
  items: string[];
  selectedItems: string[];
  onToggle: (item: string) => void;
  maxVisible?: number;
}

export function FilterChips({ 
  items, 
  selectedItems, 
  onToggle,
  maxVisible = 5 
}: FilterChipsProps) {
  const [showAll, setShowAll] = useState(false);

  if (items.length === 0) return null;

  const displayedItems = showAll ? items : items.slice(0, maxVisible);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {displayedItems.map((item) => (
        <button
          key={item}
          onClick={() => onToggle(item)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
            selectedItems.includes(item)
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
          }`}
        >
          {item}
        </button>
      ))}
      {items.length > maxVisible && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="px-3 py-1.5 rounded-full text-xs font-medium transition-all border bg-muted text-muted-foreground border-border hover:border-primary/50 hover:text-foreground flex items-center gap-1"
        >
          {showAll ? "Show Less" : `Show More (${items.length - maxVisible})`}
          <ChevronRight className={`h-3 w-3 transition-transform ${showAll ? "rotate-90" : ""}`} />
        </button>
      )}
    </div>
  );
}

