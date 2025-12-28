import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Plus,
    Settings,
    Database,
    Trash2,
    MoreVertical,
    Cpu,
    HelpCircle,
    ChevronDown
} from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

const MOCK_SESSIONS = [
    { id: 1, name: "Alan Turing", preview: "The imitation game is..." },
    { id: 2, name: "Ada Lovelace", preview: "Calculating the numbers..." },
    { id: 3, name: "Marcus Aurelius", preview: "The obstacle is the way." },
];

const FAQ_ITEMS = [
    {
        question: "How do I create a new Null?",
        answer: "Click the 'New Null' button at the top. Upload training data (text, video, or voice) to build the personality model."
    },
    {
        question: "What data can I upload?",
        answer: "Text (chat logs, interviews), Video (vlogs, presentations), and Audio (voice recordings). The AI will analyze all to replicate personality."
    },
    {
        question: "How does the AI learn?",
        answer: "Upload source materials and click 'Refresh AI Memory'. The system reindexes neural patterns to incorporate new data."
    },
    {
        question: "Can I use Call mode on mobile?",
        answer: "Yes! Switch to Call mode anytime. Use your device's speaker for voice synthesis and audio input."
    },
    {
        question: "How do I export conversations?",
        answer: "Long-press on any chat session to access options for export, backup, or archive management."
    }
];

export function Sidebar({ onOpenFiles, onOpenSettings }) {
    const [activeSession, setActiveSession] = useState(1);
    const [faqOpen, setFaqOpen] = useState(false);

    return (
        <div className="w-80 h-full bg-sidebar border-r border-white/5 flex flex-col font-sans">
            <div className="p-6">
                <div className="flex items-center gap-2 mb-8">
                    <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/20 text-primary">
                        <Cpu size={18} />
                    </div>
                    <h1 className="text-xl font-display font-bold tracking-tight text-white">Nulltale</h1>
                </div>

                <Button
                    className="w-full justify-start gap-2 bg-white/5 hover:bg-white/10 text-white border-white/5 mb-6"
                    variant="outline"
                >
                    <Plus size={16} />
                    New Null
                </Button>

                <div className="text-xs font-medium text-muted-foreground mb-4 uppercase tracking-wider">
                    Memory Banks
                </div>
            </div>

            <ScrollArea className="flex-1 px-4">
                <div className="space-y-2">
                    {MOCK_SESSIONS.map((session) => (
                        <div
                            key={session.id}
                            className={cn(
                                "group flex items-center justify-between p-3 rounded-xl transition-all duration-200 cursor-pointer border",
                                activeSession === session.id
                                    ? "bg-primary/10 border-primary/20"
                                    : "hover:bg-white/5 border-transparent hover:border-white/5"
                            )}
                            onClick={() => setActiveSession(session.id)}
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className={cn(
                                    "w-2 h-2 rounded-full",
                                    activeSession === session.id ? "bg-primary shadow-[0_0_8px_rgba(124,58,237,0.5)]" : "bg-muted-foreground/30"
                                )} />
                                <div className="flex flex-col overflow-hidden">
                                    <span className={cn(
                                        "text-sm font-medium truncate",
                                        activeSession === session.id ? "text-white" : "text-muted-foreground group-hover:text-white"
                                    )}>
                                        {session.name}
                                    </span>
                                    <span className="text-xs text-muted-foreground truncate opacity-60">
                                        {session.preview}
                                    </span>
                                </div>
                            </div>

                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <MoreVertical size={14} className="text-muted-foreground" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-40 bg-sidebar border-white/10">
                                    <DropdownMenuItem className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer">
                                        <Trash2 size={14} className="mr-2" />
                                        Delete
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    ))}
                </div>

                {/* FAQ/Guide Section */}
                <div className="px-2 py-6 border-t border-white/5 mt-4">
                    <Collapsible open={faqOpen} onOpenChange={setFaqOpen}>
                        <CollapsibleTrigger asChild>
                            <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors text-muted-foreground hover:text-white">
                                <div className="flex items-center gap-2">
                                    <HelpCircle size={16} />
                                    <span className="text-xs font-medium uppercase tracking-wider">FAQ & Guide</span>
                                </div>
                                <ChevronDown size={16} className={cn("transition-transform duration-200", faqOpen && "rotate-180")} />
                            </button>
                        </CollapsibleTrigger>

                        <CollapsibleContent className="mt-2 space-y-2">
                            {FAQ_ITEMS.map((item, idx) => (
                                <details key={idx} className="group">
                                    <summary className="cursor-pointer text-xs font-medium text-muted-foreground hover:text-white p-2 rounded-lg hover:bg-white/5 transition-colors list-none">
                                        <div className="flex items-start gap-2">
                                            <span className="text-primary mt-0.5">+</span>
                                            <span className="text-left">{item.question}</span>
                                        </div>
                                    </summary>
                                    <p className="text-[11px] text-muted-foreground/70 p-2 pl-6 leading-relaxed border-l border-white/5 ml-2">
                                        {item.answer}
                                    </p>
                                </details>
                            ))}
                        </CollapsibleContent>
                    </Collapsible>
                </div>
            </ScrollArea>

            <div className="p-4 border-t border-white/5 space-y-2">
                <Button
                    variant="ghost"
                    className="w-full justify-start gap-3 text-muted-foreground hover:text-white hover:bg-white/5"
                    onClick={onOpenFiles}
                >
                    <Database size={18} />
                    Knowledge Base
                </Button>
                <Button
                    variant="ghost"
                    className="w-full justify-start gap-3 text-muted-foreground hover:text-white hover:bg-white/5"
                    onClick={onOpenSettings}
                >
                    <Settings size={18} />
                    Settings
                </Button>
            </div>
        </div>
    );
}
