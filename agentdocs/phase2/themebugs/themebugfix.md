UI Bugfix Guide: Theme & Settings Propagation

Target: React Frontend (frontend/)
Issues Addressed: 1. The "coffee" theme does not activate when selected.
2. Changes made in the Settings Panel do not affect the rest of the application.

Root Cause Analysis

Theme Issue: DaisyUI requires explicit declaration of themes in tailwind.config.js to bundle the associated CSS variables. The 'coffee' theme was likely omitted. Furthermore, the theme must be applied as a data-theme attribute to the root <html> element.

Settings Issue: The settings state is currently "trapped" locally within SettingsPanel.tsx. To allow the PhraseAnnotator, App, and the <html> document itself to react to settings changes, the state must be lifted into a global React Context.

Required Code Changes

1. Update Tailwind Config to Include the Theme

File: frontend/tailwind.config.js
Action: Modify the daisyui configuration to explicitly include the missing themes so the CSS variables are generated.

module.exports = {
  // ... existing configuration (content, theme, plugins) ...
  daisyui: {
    themes: ["light", "dark", "coffee"], // Ensure 'coffee' is included here
  },
}


2. Create a Global Settings Context

File: frontend/src/context/SettingsContext.tsx (Create this new file)
Action: Implement a Context Provider that holds the settings state and applies the theme to the DOM.

import React, { createContext, useContext, useState, useEffect } from 'react';

// Define the shape of your global settings
interface Settings {
  theme: string;
  showSuggestions: boolean;
  // add other settings like autoSave, showTooltips, etc.
}

interface SettingsContextType {
  settings: Settings;
  updateSetting: (key: keyof Settings, value: any) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<Settings>({
    theme: 'dark', // default theme
    showSuggestions: true,
  });

  const updateSetting = (key: keyof Settings, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  // The critical piece: Listen for theme changes and update the HTML tag
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme);
  }, [settings.theme]);

  return (
    <SettingsContext.Provider value={{ settings, updateSetting }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};


3. Wrap the Application with the Provider

File: frontend/src/App.tsx (or frontend/src/index.tsx)
Action: Wrap the root component structure with SettingsProvider so all child components can access the global settings.

// ... existing imports ...
import { SettingsProvider } from './context/SettingsContext';

function App() {
  return (
    <SettingsProvider>
      <div className="App">
         {/* ... existing app structure (Header, PhraseAnnotator, SettingsPanel, etc.) ... */}
      </div>
    </SettingsProvider>
  );
}

export default App;


4. Refactor SettingsPanel to Use Context

File: frontend/src/components/SettingsPanel.tsx
Action: Remove local useState hooks for settings and replace them with the useSettings hook.

// ... existing imports ...
import { useSettings } from '../context/SettingsContext';

export const SettingsPanel = () => {
  // Replace local state with global context
  const { settings, updateSetting } = useSettings();

  return (
    <div className="settings-panel">
      {/* Example: Wiring up the Theme Dropdown */}
      <div className="form-control w-full max-w-xs">
        <label className="label">
          <span className="label-text">Theme</span>
        </label>
        <select 
          value={settings.theme} 
          onChange={(e) => updateSetting('theme', e.target.value)}
          className="select select-bordered w-full max-w-xs"
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="coffee">Coffee</option>
        </select>
      </div>

      {/* Example: Wiring up a Toggle */}
      <div className="form-control w-52">
        <label className="cursor-pointer label">
          <span className="label-text">Show Suggestions</span> 
          <input 
            type="checkbox" 
            checked={settings.showSuggestions}
            onChange={(e) => updateSetting('showSuggestions', e.target.checked)}
            className="toggle toggle-primary" 
          />
        </label>
      </div>
      
      {/* ... wire up remaining settings inputs similarly ... */}
    </div>
  );
};


Summary for the Agent

By implementing these four steps, the state is no longer localized in SettingsPanel. The SettingsProvider handles the DOM manipulation required for DaisyUI themes (document.documentElement.setAttribute), and any child component (like PhraseAnnotator) can now call const { settings } = useSettings() to reactively re-render when a user changes a toggle.