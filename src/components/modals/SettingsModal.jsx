import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function SettingsModal({ open, onOpenChange }) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] bg-sidebar border-white/10 text-white">
                <DialogHeader>
                    <DialogTitle className="font-display tracking-tight">System Settings</DialogTitle>
                </DialogHeader>

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
                            <Select defaultValue="v2.4">
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
                                <span className="text-xs text-muted-foreground">0.7</span>
                            </div>
                            <Slider defaultValue={[0.7]} max={1} step={0.1} className="[&>span:first-child]:bg-primary" />
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">API Keys</h4>
                        <div className="grid gap-2">
                            <Label>OpenAI API Key</Label>
                            <Input type="password" value="sk-........................" className="bg-white/5 border-white/10 font-mono" readOnly />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button onClick={() => onOpenChange(false)} className="bg-primary text-white hover:bg-primary/90">Save Settings</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
