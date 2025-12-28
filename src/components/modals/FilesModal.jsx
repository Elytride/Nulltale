import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { FileText, Video, Mic, Upload, RefreshCw } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { motion, AnimatePresence } from "framer-motion";

export function FilesModal({ open, onOpenChange }) {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [progress, setProgress] = useState(0);

    const handleRefresh = () => {
        setIsRefreshing(true);
        setProgress(0);

        // Simulate training progress
        const interval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 100) {
                    clearInterval(interval);
                    setTimeout(() => setIsRefreshing(false), 1000);
                    return 100;
                }
                return prev + 2;
            });
        }, 50);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[700px] bg-sidebar border-white/10 text-white shadow-2xl">
                <DialogHeader>
                    <DialogTitle className="text-xl font-display tracking-tight">Knowledge Base</DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Manage the data sources used to reconstruct the personality.
                    </DialogDescription>
                </DialogHeader>

                <div className="mt-6">
                    <Tabs defaultValue="text" className="w-full">
                        <TabsList className="grid w-full grid-cols-3 bg-white/5 border border-white/5">
                            <TabsTrigger value="text" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
                                <FileText className="w-4 h-4 mr-2" />
                                Text Logs
                            </TabsTrigger>
                            <TabsTrigger value="video" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
                                <Video className="w-4 h-4 mr-2" />
                                Video
                            </TabsTrigger>
                            <TabsTrigger value="voice" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
                                <Mic className="w-4 h-4 mr-2" />
                                Voice
                            </TabsTrigger>
                        </TabsList>

                        <div className="p-6 border border-white/5 border-t-0 rounded-b-lg bg-black/20 min-h-[300px]">
                            <TabsContent value="text" className="space-y-4 mt-0">
                                <div className="border-2 border-dashed border-white/10 rounded-lg p-8 flex flex-col items-center justify-center text-center hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer group">
                                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:bg-primary/20 group-hover:text-primary transition-colors">
                                        <Upload size={24} />
                                    </div>
                                    <p className="text-sm font-medium">Drop chat logs or text files here</p>
                                    <p className="text-xs text-muted-foreground mt-1">TXT, PDF, JSON supported</p>
                                </div>

                                <div className="space-y-3 pt-4">
                                    <Label>Additional Context</Label>
                                    <Textarea
                                        placeholder="Enter specific personality traits, key memories, or behavioral quirks here..."
                                        className="bg-white/5 border-white/10 focus-visible:ring-primary min-h-[120px]"
                                    />
                                </div>
                            </TabsContent>

                            <TabsContent value="video" className="mt-0">
                                <div className="border-2 border-dashed border-white/10 rounded-lg p-12 flex flex-col items-center justify-center text-center hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer group h-[300px]">
                                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:bg-primary/20 group-hover:text-primary transition-colors">
                                        <Video size={24} />
                                    </div>
                                    <p className="text-sm font-medium">Upload interviews or vlogs</p>
                                    <p className="text-xs text-muted-foreground mt-1">MP4, MOV up to 500MB</p>
                                </div>
                            </TabsContent>

                            <TabsContent value="voice" className="mt-0">
                                <div className="border-2 border-dashed border-white/10 rounded-lg p-12 flex flex-col items-center justify-center text-center hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer group h-[300px]">
                                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:bg-primary/20 group-hover:text-primary transition-colors">
                                        <Mic size={24} />
                                    </div>
                                    <p className="text-sm font-medium">Upload voice notes or recordings</p>
                                    <p className="text-xs text-muted-foreground mt-1">MP3, WAV for voice synthesis</p>
                                </div>
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>

                <div className="mt-6">
                    <AnimatePresence mode="wait">
                        {isRefreshing ? (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="space-y-2"
                            >
                                <div className="flex justify-between text-xs font-medium text-primary">
                                    <span>Reindexing Neural Patterns...</span>
                                    <span>{progress}%</span>
                                </div>
                                <Progress value={progress} className="h-2 bg-white/10" />
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                <Button
                                    onClick={handleRefresh}
                                    className="w-full bg-gradient-to-r from-primary to-blue-600 hover:from-primary/90 hover:to-blue-600/90 text-white shadow-lg shadow-primary/20 h-12 text-md font-medium"
                                >
                                    <RefreshCw className="mr-2 w-5 h-5" />
                                    Refresh AI Memory
                                </Button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </DialogContent>
        </Dialog>
    );
}
