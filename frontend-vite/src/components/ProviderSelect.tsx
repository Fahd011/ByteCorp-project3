import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Provider } from "@/types";

interface ProviderSelectProps {
  value: string;
  onValueChange: (value: string) => void;
  providers: Provider[];
  id?: string;
  label?: string;
}

export function ProviderSelect({ 
  value, 
  onValueChange, 
  providers, 
  id = "provider-select",
  label = "Provider"
}: ProviderSelectProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id={id}>
          <SelectValue placeholder="Select a provider..." />
        </SelectTrigger>
        <SelectContent className="max-h-[300px]">
          {providers.length > 0 ? (
            providers.map((provider: Provider) => (
              <SelectItem key={provider.id} value={provider.id}>
                {provider.name}
              </SelectItem>
            ))
          ) : (
            <SelectItem value="loading" disabled>Loading providers...</SelectItem>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

