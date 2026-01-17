import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getSettings, updateSettings, getWaveSpeedKeyStatus, saveWaveSpeedKey, testWaveSpeedKey, deleteWaveSpeedKey } from "@/lib/api";
import { Loader2, Check, X, Eye, EyeOff, KeyRound, Trash2 } from "lucide-react";

export function SettingsModal({ open, onOpenChange }) {
    const [settings, setSettings] = useState({
        model_version: "v2.4",
        temperature: 0.7,
        api_key: "sk-........................"
    });
    const [isSaving, setIsSaving] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // WaveSpeed API key state (separate from main settings)
    const [wavespeedKey, setWavespeedKey] = useState("");
    const [wavespeedKeyConfigured, setWavespeedKeyConfigured] = useState(false);
    const [showWavespeedKey, setShowWavespeedKey] = useState(false);
    const [isSavingKey, setIsSavingKey] = useState(false);
    const [isTestingKey, setIsTestingKey] = useState(false);
    const [keyStatus, setKeyStatus] = useState(null); // 'success', 'error', or null

    // Fetch settings when modal opens
    useEffect(() => {
        if (open) {
            async function fetchSettings() {
                setIsLoading(true);
                try {
                    // Fetch main settings
                    const data = await getSettings();
                    setSettings(data);

                    // Fetch WaveSpeed key status
                    const keyStatus = await getWaveSpeedKeyStatus();
                    setWavespeedKeyConfigured(keyStatus.configured);
                    setWavespeedKey(""); // Don't show actual key
                } catch (error) {
                    console.error("Failed to fetch settings:", error);
                } finally {
                    setIsLoading(false);
                }
            }
            fetchSettings();
        }
    }, [open]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await updateSettings(settings);
            onOpenChange(false);
        } catch (error) {
            console.error("Failed to save settings:", error);
            alert("Failed to save settings. Please try again.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleSaveWavespeedKey = async () => {
        if (!wavespeedKey.trim()) return;

        setIsSavingKey(true);
        setKeyStatus(null);
        try {
            await saveWaveSpeedKey(wavespeedKey);
            setWavespeedKeyConfigured(true);
            setWavespeedKey(""); // Clear input after save
            setKeyStatus('success');
            setTimeout(() => setKeyStatus(null), 3000);
        } catch (error) {
            console.error("Failed to save WaveSpeed key:", error);
            setKeyStatus('error');
        } finally {
            setIsSavingKey(false);
        }
    };

    const handleTestKey = async () => {
        setIsTestingKey(true);
        setKeyStatus(null);
        try {
            await testWaveSpeedKey();
            setKeyStatus('success');
            setTimeout(() => setKeyStatus(null), 3000);
        } catch (error) {
            console.error("WaveSpeed key test failed:", error);
            setKeyStatus('error');
            alert(`API key test failed: ${error.message}`);
        } finally {
            setIsTestingKey(false);
        }
    };

    const handleDeleteKey = async () => {
        if (!confirm("Are you sure you want to remove the WaveSpeed API key?")) return;

        try {
            await deleteWaveSpeedKey();
            setWavespeedKeyConfigured(false);
            setWavespeedKey("");
            setKeyStatus(null);
        } catch (error) {
            console.error("Failed to delete WaveSpeed key:", error);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] bg-sidebar border-white/10 text-white">
                <DialogHeader>
                    <DialogTitle className="font-display tracking-tight">System Settings</DialogTitle>
                </DialogHeader>

                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <div className="grid gap-6 py-4">
                        <div className="space-y-4">
                            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Appearance</h4>
                            <div className="flex items-center justify-between">
                                <Label htmlFor="theme" className="flex flex-col gap-1">
                                    <span>Dark Mode</span>
                                    <span className="font-normal text-xs text-muted-foreground">Always active in Nulltale</span>
                                </Label>
                                <Switch id="theme" checked disabled />
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">AI Configuration</h4>

                            <div className="grid gap-2">
                                <Label>Model Version</Label>
                                <Select
                                    value={settings.model_version}
                                    onValueChange={(value) => setSettings(prev => ({ ...prev, model_version: value }))}
                                >
                                    <SelectTrigger className="bg-white/5 border-white/10">
                                        <SelectValue placeholder="Select model" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-sidebar border-white/10 text-white">
                                        <SelectItem value="v2.4">Nulltale v2.4 (Stable)</SelectItem>
                                        <SelectItem value="v3.0">Nulltale v3.0 (Beta)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="grid gap-4">
                                <div className="flex items-center justify-between">
                                    <Label>Creativity Temperature</Label>
                                    <span className="text-xs text-muted-foreground">{settings.temperature.toFixed(1)}</span>
                                </div>
                                <Slider
                                    value={[settings.temperature]}
                                    onValueChange={([value]) => setSettings(prev => ({ ...prev, temperature: value }))}
                                    max={1}
                                    step={0.1}
                                    className="[&>span:first-child]:bg-primary"
                                />
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                <KeyRound className="w-4 h-4" />
                                Voice Synthesis
                            </h4>

                            <div className="grid gap-3">
                                <div className="flex items-center justify-between">
                                    <Label>WaveSpeed API Key</Label>
                                    {wavespeedKeyConfigured && (
                                        <span className="flex items-center gap-1 text-xs text-green-400">
                                            <Check className="w-3 h-3" />
                                            Configured
                                        </span>
                                    )}
                                </div>

                                <div className="flex gap-2">
                                    <div className="relative flex-1">
                                        <Input
                                            type={showWavespeedKey ? "text" : "password"}
                                            value={wavespeedKey}
                                            onChange={(e) => setWavespeedKey(e.target.value)}
                                            placeholder={wavespeedKeyConfigured ? "Enter new key to update..." : "Enter your API key..."}
                                            className="bg-white/5 border-white/10 font-mono pr-10"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowWavespeedKey(!showWavespeedKey)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                                        >
                                            {showWavespeedKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>

                                    <Button
                                        size="sm"
                                        onClick={handleSaveWavespeedKey}
                                        disabled={!wavespeedKey.trim() || isSavingKey}
                                        className="bg-primary hover:bg-primary/90"
                                    >
                                        {isSavingKey ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : keyStatus === 'success' ? (
                                            <Check className="w-4 h-4" />
                                        ) : keyStatus === 'error' ? (
                                            <X className="w-4 h-4" />
                                        ) : (
                                            "Save"
                                        )}
                                    </Button>
                                </div>

                                {wavespeedKeyConfigured && (
                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={handleTestKey}
                                            disabled={isTestingKey}
                                            className="flex-1 border-white/10 hover:bg-white/5"
                                        >
                                            {isTestingKey ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                    Testing...
                                                </>
                                            ) : (
                                                "Test Connection"
                                            )}
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleDeleteKey}
                                            className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                )}

                                <p className="text-xs text-muted-foreground">
                                    Get your key from <a href="https://wavespeed.ai" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">wavespeed.ai</a>.
                                    Required for custom voice cloning. Your key is stored securely and encrypted locally.
                                </p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">API Keys</h4>
                            <div className="grid gap-2">
                                <Label>OpenAI API Key</Label>
                                <Input
                                    type="password"
                                    value={settings.api_key}
                                    onChange={(e) => setSettings(prev => ({ ...prev, api_key: e.target.value }))}
                                    className="bg-white/5 border-white/10 font-mono"
                                />
                            </div>
                        </div>
                    </div>
                )}

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button
                        onClick={handleSave}
                        className="bg-primary text-white hover:bg-primary/90"
                        disabled={isSaving || isLoading}
                    >
                        {isSaving ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            "Save Settings"
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
