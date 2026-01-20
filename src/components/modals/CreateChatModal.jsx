import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createSession } from "@/lib/api";

export function CreateChatModal({ open, onOpenChange, onSessionCreated }) {
    const [name, setName] = useState("");
    const [isCreating, setIsCreating] = useState(false);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!name.trim()) return;

        setIsCreating(true);
        try {
            const newSession = await createSession(name);
            onSessionCreated(newSession);
            onOpenChange(false);
            setName(""); // Reset form
        } catch (error) {
            console.error("Failed to create chat:", error);
            // Ideally show error toast/message
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px] bg-sidebar border-white/10 text-white">
                <DialogHeader>
                    <DialogTitle>New Chat</DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Give your new personality a name to get started.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreate} className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Name</Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. John Doe"
                            className="bg-white/5 border-white/10"
                            autoFocus
                        />
                    </div>
                    <DialogFooter>
                        <Button type="submit" disabled={!name.trim() || isCreating}>
                            {isCreating ? "Creating..." : "Create & Manage Files"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
