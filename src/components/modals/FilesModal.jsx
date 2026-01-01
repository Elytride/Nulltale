import { useState, useRef, useCallback, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Mic, Upload, RefreshCw, Check, X, MessageSquare, Instagram, HelpCircle, User, Trash2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { motion, AnimatePresence } from "framer-motion";
import { uploadFile, refreshAIMemory, checkRefreshReady, setSubject, deleteUploadedFile, listFiles } from "@/lib/api";
import { cn } from "@/lib/utils";

// File type badge component
function FileTypeBadge({ type }) {
    const configs = {
        WhatsApp: { bg: "bg-green-500/20", text: "text-green-400", icon: MessageSquare, label: "WhatsApp" },
        Instagram: { bg: "bg-pink-500/20", text: "text-pink-400", icon: Instagram, label: "Instagram" },
        voice: { bg: "bg-purple-500/20", text: "text-purple-400", icon: Mic, label: "Voice" },
        NULL: { bg: "bg-gray-500/20", text: "text-gray-400", icon: HelpCircle, label: "Unknown" },
        unknown: { bg: "bg-gray-500/20", text: "text-gray-400", icon: HelpCircle, label: "Unknown" }
    };

    const config = configs[type] || configs.unknown;
    const Icon = config.icon;

    return (
        <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium", config.bg, config.text)}>
            <Icon size={12} />
            {config.label}
        </span>
    );
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export function FilesModal({ open, onOpenChange }) {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [uploadedFiles, setUploadedFiles] = useState({ text: [], voice: [] });
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const [rejectedFiles, setRejectedFiles] = useState([]);
    const [refreshReady, setRefreshReady] = useState({ ready: false, reason: '' });
    const [refreshError, setRefreshError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);

    const textInputRef = useRef(null);
    const voiceInputRef = useRef(null);

    // Load files from server on modal open
    useEffect(() => {
        if (open) {
            refreshFileList();
        }
    }, [open]);

    const refreshFileList = async () => {
        try {
            const [textResult, voiceResult, readyResult] = await Promise.all([
                listFiles("text"),
                listFiles("voice"),
                checkRefreshReady()
            ]);
            setUploadedFiles({
                text: textResult.files || [],
                voice: voiceResult.files || []
            });
            setRefreshReady(readyResult);
        } catch (error) {
            console.error("Failed to load files:", error);
        }
    };

    const handleRefresh = async () => {
        setIsRefreshing(true);
        setProgress(0);
        setProgressMessage('Starting...');
        setRefreshError(null);

        await refreshAIMemory({
            onProgress: (data) => {
                setProgress(Math.round(data.progress));
                setProgressMessage(data.message);
            },
            onComplete: (data) => {
                setProgress(100);
                setProgressMessage(data.message);
                setTimeout(() => {
                    setIsRefreshing(false);
                    setProgressMessage('');
                    setSuccessMessage('AI Memory refreshed successfully!');
                    // Auto-dismiss after 5 seconds
                    setTimeout(() => setSuccessMessage(null), 5000);
                }, 1000);
            },
            onError: (message) => {
                setRefreshError(message);
                setIsRefreshing(false);
                setProgressMessage('');
            }
        });
    };

    const handleFileUpload = async (files, fileType) => {
        if (!files || files.length === 0) return;

        setUploading(true);
        setUploadError(null);
        setRejectedFiles([]);

        try {
            const result = await uploadFile(files, fileType);

            // Handle rejected files
            if (result.rejected && result.rejected.length > 0) {
                setRejectedFiles(result.rejected);
            }

            // Refresh file list to get latest from server
            await refreshFileList();

        } catch (error) {
            console.error("Failed to upload files:", error);
            setUploadError("Failed to upload files. Please try again.");
        } finally {
            setUploading(false);
        }
    };

    const handleSubjectChange = async (fileType, fileId, subject) => {
        try {
            await setSubject(fileType, fileId, subject);
            // Update local state
            setUploadedFiles(prev => ({
                ...prev,
                [fileType]: prev[fileType].map(f =>
                    f.id === fileId ? { ...f, subject } : f
                )
            }));
        } catch (error) {
            console.error("Failed to set subject:", error);
        }
    };

    const handleDeleteFile = async (fileType, fileId) => {
        try {
            await deleteUploadedFile(fileType, fileId);
            // Refresh list from server
            await refreshFileList();
        } catch (error) {
            console.error("Failed to delete file:", error);
        }
    };

    const handleFileSelect = (e, fileType) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            handleFileUpload(files, fileType);
        }
        e.target.value = '';
    };

    const handleDrop = useCallback((e, fileType) => {
        e.preventDefault();
        e.stopPropagation();

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleFileUpload(files, fileType);
        }
    }, []);

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const UploadZone = ({ fileType, icon: Icon, title, accept, inputRef, description }) => (
        <>
            <input
                type="file"
                ref={inputRef}
                onChange={(e) => handleFileSelect(e, fileType)}
                className="hidden"
                accept={accept}
                multiple
            />
            <div
                className="border-2 border-dashed border-white/10 rounded-lg p-8 flex flex-col items-center justify-center text-center hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer group"
                onClick={() => inputRef.current?.click()}
                onDrop={(e) => handleDrop(e, fileType)}
                onDragOver={handleDragOver}
            >
                <div className={cn(
                    "w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 transition-colors",
                    uploading ? "animate-pulse" : "group-hover:bg-primary/20 group-hover:text-primary"
                )}>
                    <Icon size={24} />
                </div>
                <p className="text-sm font-medium">{title}</p>
                <p className="text-xs text-muted-foreground mt-1">{description}</p>
                <p className="text-xs text-muted-foreground mt-1">Drop multiple files or click to browse</p>
                {uploading && <p className="text-xs text-primary mt-2">Uploading...</p>}
            </div>

            {/* Rejected files notification */}
            {rejectedFiles.length > 0 && fileType === "text" && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-red-400 text-sm font-medium">
                            <AlertCircle size={16} />
                            Some files were rejected
                        </div>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-red-400 hover:text-red-300 hover:bg-red-500/20"
                            onClick={() => setRejectedFiles([])}
                        >
                            <X size={14} />
                        </Button>
                    </div>
                    {rejectedFiles.map((file, idx) => (
                        <div key={idx} className="text-xs text-red-300 pl-6">
                            <span className="font-medium">{file.name}:</span> {file.reason}
                        </div>
                    ))}
                </div>
            )}

            {/* Uploaded files list */}
            {uploadedFiles[fileType].length > 0 && (
                <div className="mt-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <Label className="text-xs text-muted-foreground">
                            Files ({uploadedFiles[fileType].length})
                        </Label>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs text-muted-foreground hover:text-white"
                            onClick={refreshFileList}
                        >
                            <RefreshCw size={12} className="mr-1" />
                            Refresh
                        </Button>
                    </div>
                    {uploadedFiles[fileType].map((file) => (
                        <div key={file.id} className="bg-white/5 rounded-lg p-3 space-y-2">
                            {/* File header */}
                            <div className="flex items-center gap-2">
                                <Check size={14} className="text-green-500 flex-shrink-0" />
                                <span className="truncate flex-1 text-sm">{file.original_name || file.saved_as}</span>
                                {file.size && (
                                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                                )}
                                <FileTypeBadge type={file.detected_type} />
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 text-muted-foreground hover:text-red-400"
                                    onClick={() => handleDeleteFile(fileType, file.id)}
                                >
                                    <Trash2 size={14} />
                                </Button>
                            </div>

                            {/* Subject selector for text files */}
                            {fileType === "text" && file.participants && file.participants.length > 0 && (
                                <div className="flex items-center gap-2 pl-6">
                                    <User size={12} className="text-muted-foreground" />
                                    <Select
                                        value={file.subject || ""}
                                        onValueChange={(value) => handleSubjectChange(fileType, file.id, value)}
                                    >
                                        <SelectTrigger className="h-8 text-xs bg-white/5 border-white/10 flex-1">
                                            <SelectValue placeholder="Select subject..." />
                                        </SelectTrigger>
                                        <SelectContent className="bg-sidebar border-white/10">
                                            {file.participants.map((participant) => (
                                                <SelectItem
                                                    key={participant}
                                                    value={participant}
                                                    className="text-xs"
                                                >
                                                    {participant}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {file.subject && (
                                        <span className="text-xs text-green-400">✓</span>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </>
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[700px] bg-sidebar border-white/10 text-white shadow-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="text-xl font-display tracking-tight">Knowledge Base</DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Manage the data sources used to reconstruct the personality.
                    </DialogDescription>
                </DialogHeader>

                {uploadError && (
                    <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                        <X size={16} />
                        {uploadError}
                    </div>
                )}

                {successMessage && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400"
                    >
                        <CheckCircle2 size={24} className="flex-shrink-0" />
                        <div className="flex-1">
                            <p className="font-medium">Success!</p>
                            <p className="text-sm text-green-300">{successMessage}</p>
                        </div>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-green-400 hover:text-green-300 hover:bg-green-500/20"
                            onClick={() => setSuccessMessage(null)}
                        >
                            <X size={14} />
                        </Button>
                    </motion.div>
                )}

                <div className="mt-6">
                    <Tabs defaultValue="text" className="w-full">
                        <TabsList className="grid w-full grid-cols-2 bg-white/5 border border-white/5">
                            <TabsTrigger value="text" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
                                <FileText className="w-4 h-4 mr-2" />
                                Chat Logs
                            </TabsTrigger>
                            <TabsTrigger value="voice" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
                                <Mic className="w-4 h-4 mr-2" />
                                Voice
                            </TabsTrigger>
                        </TabsList>

                        <div className="p-6 border border-white/5 border-t-0 rounded-b-lg bg-black/20 min-h-[300px]">
                            <TabsContent value="text" className="space-y-4 mt-0">
                                <UploadZone
                                    fileType="text"
                                    icon={Upload}
                                    title="Drop WhatsApp or Instagram chat exports"
                                    accept=".txt,.json"
                                    inputRef={textInputRef}
                                    description="Only .txt and .json files are accepted"
                                />

                                <div className="space-y-3 pt-4">
                                    <Label>Additional Context</Label>
                                    <Textarea
                                        placeholder="Enter specific personality traits, key memories, or behavioral quirks here..."
                                        className="bg-white/5 border-white/10 focus-visible:ring-primary min-h-[100px]"
                                    />
                                </div>
                            </TabsContent>

                            <TabsContent value="voice" className="mt-0">
                                <UploadZone
                                    fileType="voice"
                                    icon={Mic}
                                    title="Upload voice notes or recordings"
                                    accept=".mp3,.wav,.ogg,.m4a"
                                    inputRef={voiceInputRef}
                                    description="MP3, WAV for voice synthesis"
                                />
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>

                <div className="mt-6">
                    {refreshError && (
                        <div className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                            <AlertCircle size={16} />
                            {refreshError}
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 ml-auto text-red-400 hover:text-red-300"
                                onClick={() => setRefreshError(null)}
                            >
                                <X size={14} />
                            </Button>
                        </div>
                    )}

                    <AnimatePresence mode="wait">
                        {isRefreshing ? (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="space-y-2"
                            >
                                <div className="flex justify-between text-xs font-medium text-primary">
                                    <span className="truncate">{progressMessage || 'Processing...'}</span>
                                    <span>{progress}%</span>
                                </div>
                                <Progress value={progress} className="h-2 bg-white/10" />
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="space-y-2"
                            >
                                {!refreshReady.ready && (
                                    <p className="text-xs text-muted-foreground text-center mb-2">
                                        {refreshReady.reason || 'Upload files and select subjects to enable processing'}
                                    </p>
                                )}
                                <Button
                                    onClick={handleRefresh}
                                    disabled={!refreshReady.ready}
                                    className={cn(
                                        "w-full h-12 text-md font-medium transition-all",
                                        refreshReady.ready
                                            ? "bg-gradient-to-r from-primary to-blue-600 hover:from-primary/90 hover:to-blue-600/90 text-white shadow-lg shadow-primary/20"
                                            : "bg-white/5 text-muted-foreground cursor-not-allowed"
                                    )}
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
