import { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatInterface } from "@/components/layout/ChatInterface";
import { FilesModal } from "@/components/modals/FilesModal";
import { SettingsModal } from "@/components/modals/SettingsModal";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu, Cpu, MessageSquare, Database, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
    const [filesOpen, setFilesOpen] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [currentSession, setCurrentSession] = useState(null);

    const handleOpenFiles = () => {
        setFilesOpen(true);
        setSidebarOpen(false);
    };

    const handleOpenSettings = () => {
        setSettingsOpen(true);
        setSidebarOpen(false);
    };

    const handleSessionChange = (session) => {
        setCurrentSession(session);
        setSidebarOpen(false);
    };

    return (
        <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
            {/* Desktop Sidebar */}
            <div className="hidden lg:flex">
                <Sidebar
                    onOpenFiles={handleOpenFiles}
                    onOpenSettings={handleOpenSettings}
                    onSessionChange={handleSessionChange}
                />
            </div>

            {/* Mobile Sidebar Drawer */}
            <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
                <SheetContent side="left" className="w-80 p-0 border-white/5 bg-sidebar">
                    <Sidebar
                        onOpenFiles={handleOpenFiles}
                        onOpenSettings={handleOpenSettings}
                        onSessionChange={handleSessionChange}
                    />
                </SheetContent>
            </Sheet>

            {/* Chat Area */}
            <main className="flex-1 flex flex-col relative h-full w-full lg:w-auto">
                {/* Mobile Menu Button */}
                <div className="lg:hidden h-16 border-b border-white/5 flex items-center px-4 bg-background/50 backdrop-blur-sm">
                    <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="text-white">
                                <Menu size={24} />
                            </Button>
                        </SheetTrigger>
                    </Sheet>
                </div>

                {currentSession ? (
                    <ChatInterface
                        sessionId={currentSession.id}
                        sessionName={currentSession.name}
                    />
                ) : (
                    /* Nulltale Home Screen */
                    <div className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-hidden">
                        {/* Background Effects */}
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(120,58,237,0.15),transparent_50%)] pointer-events-none" />
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(59,130,246,0.1),transparent_40%)] pointer-events-none" />

                        {/* Logo */}
                        <div className="relative mb-8">
                            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary/30 to-blue-500/20 flex items-center justify-center border border-primary/30 shadow-2xl shadow-primary/20">
                                <Cpu size={48} className="text-primary" />
                            </div>
                            <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-background animate-pulse shadow-lg shadow-green-500/50" />
                        </div>

                        {/* Title */}
                        <h1 className="text-4xl font-display font-bold text-white mb-3 tracking-tight">
                            Nulltale
                        </h1>
                        <p className="text-muted-foreground text-center max-w-md mb-8">
                            Resurrect digital personalities from chat histories. Upload your data, train the AI, and start a conversation.
                        </p>

                        {/* Feature Cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full mb-8">
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                                <Database size={24} className="text-primary mx-auto mb-2" />
                                <h3 className="text-sm font-medium text-white mb-1">1. Upload Data</h3>
                                <p className="text-xs text-muted-foreground">Chat logs from WhatsApp or Instagram</p>
                            </div>
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                                <Sparkles size={24} className="text-primary mx-auto mb-2" />
                                <h3 className="text-sm font-medium text-white mb-1">2. Train AI</h3>
                                <p className="text-xs text-muted-foreground">Click Refresh AI Memory</p>
                            </div>
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                                <MessageSquare size={24} className="text-primary mx-auto mb-2" />
                                <h3 className="text-sm font-medium text-white mb-1">3. Start Chatting</h3>
                                <p className="text-xs text-muted-foreground">Create a new chat to begin</p>
                            </div>
                        </div>

                        {/* CTA */}
                        <p className="text-xs text-muted-foreground/60 font-mono">
                            SELECT A CHAT OR CREATE NEW TO BEGIN
                        </p>
                    </div>
                )}
            </main>

            <FilesModal open={filesOpen} onOpenChange={setFilesOpen} currentSession={currentSession} />
            <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
        </div>
    );
}
