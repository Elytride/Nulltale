import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs";
import { HelpCircle, Database, MessageSquare, Instagram, Phone, MessageCircle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

import Discdemo1 from "@/images/Discdemo/Discdemo1.jpg";
import Discdemo2 from "@/images/Discdemo/Discdemo2.jpg";
import Discdemo3 from "@/images/Discdemo/Discdemo3.jpg";

import Instademo1 from "@/images/Instademo/Instademo1.jpg";
import Instademo2 from "@/images/Instademo/Instademo2.jpg";
import Instademo3 from "@/images/Instademo/Instademo3.jpg";
import Instademo4 from "@/images/Instademo/Instademo4.jpg";
import Instademo5 from "@/images/Instademo/Instademo5.jpg";
import Instademo6 from "@/images/Instademo/Instademo6.jpg";
import Instademo7 from "@/images/Instademo/Instademo7.jpg";
import Instademo8 from "@/images/Instademo/Instademo8.jpg";
import Instademo9 from "@/images/Instademo/Instademo9.jpg";

import Whatsapp1 from "@/images/Whatsappdemo/whatsapp1.jpg";
import Whatsapp2 from "@/images/Whatsappdemo/whatsapp2.jpg";
import Whatsapp3 from "@/images/Whatsappdemo/whatsapp3.jpg";

import Line1 from "@/images/linedemo/line1.png";
import Line2 from "@/images/linedemo/line2.png";
import Line3 from "@/images/linedemo/line3.png";
import Line4 from "@/images/linedemo/line4.png";

const FAQ_ITEMS = [
    {
        question: "How do I create a new Chat?",
        answer: "Click the 'New Chat' button at the top. Make sure you've uploaded training data and refreshed AI Memory first."
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

const DATA_GUIDES = [
    {
        id: "discord",
        title: "Discord",
        icon: <MessageSquare className="text-[#5865F2]" size={18} />,
        description: "Export your personal data package.",
        steps: [
            { img: Discdemo1, label: "1. Go to User Settings" },
            { img: Discdemo2, label: "2. Scroll to 'Privacy & Safety'" },
            { img: Discdemo3, label: "3. Request Data Package" }
        ]
    },
    {
        id: "instagram",
        title: "Instagram",
        icon: <Instagram className="text-[#E1306C]" size={18} />,
        description: "Download your information (JSON format).",
        steps: [
            { img: Instademo1, label: "1. Go to Your Activity" },
            { img: Instademo2, label: "2. Download Your Information" },
            { img: Instademo3, label: "3. Request a Download" },
            { img: Instademo4, label: "4. Select Information Types" },
            { img: Instademo5, label: "5. Select 'Messages'" },
            { img: Instademo6, label: "6. Date Range: All time" },
            { img: Instademo7, label: "7. Format: JSON" },
            { img: Instademo8, label: "8. Submit Request" },
            { img: Instademo9, label: "9. Download when ready" }
        ]
    },
    {
        id: "whatsapp",
        title: "WhatsApp",
        icon: <Phone className="text-[#25D366]" size={18} />,
        description: "Export chat history to .txt",
        steps: [
            { img: Whatsapp1, label: "1. Open Chat Info" },
            { img: Whatsapp2, label: "2. Export Chat" },
            { img: Whatsapp3, label: "3. Without Media (recommended)" }
        ]
    },
    {
        id: "line",
        title: "LINE",
        icon: <MessageCircle className="text-[#00B900]" size={18} />,
        description: "Save chat history.",
        steps: [
            { img: Line1, label: "1. Settings" },
            { img: Line2, label: "2. Chats" },
            { img: Line3, label: "3. Back up and restore chat history" },
            { img: Line4, label: "4. Back up now" }
        ]
    }
];

export function FAQModal({ open, onOpenChange }) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-5xl bg-zinc-950 border-white/10 text-white h-[85vh] flex flex-col">
                <DialogHeader className="pb-4 border-b border-white/5 mx-6 pt-6">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="p-2 rounded-lg bg-primary/20 text-primary">
                            <HelpCircle size={20} />
                        </div>
                        <DialogTitle className="text-xl">Help & Guide</DialogTitle>
                    </div>
                    <DialogDescription className="text-zinc-400">
                        Everything you need to know about creating and managing personas.
                    </DialogDescription>
                </DialogHeader>

                <Tabs defaultValue="faq" className="flex-1 flex flex-col overflow-hidden">
                    <div className="px-6 py-2 border-b border-white/5 bg-zinc-950/50">
                        <TabsList className="grid w-full grid-cols-2 bg-zinc-900/50">
                            <TabsTrigger value="faq" className="hidden sm:inline-flex">Frequently Asked Questions</TabsTrigger>
                            <TabsTrigger value="faq" className="sm:hidden">FAQ</TabsTrigger>
                            <TabsTrigger value="data">How to Get Data</TabsTrigger>
                        </TabsList>
                    </div>

                    <div className="flex-1 overflow-y-auto px-6 py-4">
                        <TabsContent value="faq" className="mt-0 space-y-4 h-full">
                            <Accordion type="single" collapsible className="w-full">
                                {FAQ_ITEMS.map((item, idx) => (
                                    <AccordionItem key={idx} value={`item-${idx}`} className="border-white/10">
                                        <AccordionTrigger className="text-sm font-medium hover:text-primary transition-colors hover:no-underline text-left">
                                            {item.question}
                                        </AccordionTrigger>
                                        <AccordionContent className="text-zinc-400 text-sm leading-relaxed">
                                            {item.answer}
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        </TabsContent>

                        <TabsContent value="data" className="mt-0 h-full overflow-hidden flex flex-col">
                            <div className="p-4 rounded-xl bg-white/5 border border-white/5 mb-4 shrink-0">
                                <h3 className="flex items-center gap-2 text-sm font-medium text-white mb-2">
                                    <Database size={16} className="text-primary" />
                                    Data Collection Guide
                                </h3>
                                <p className="text-xs text-zinc-400 leading-relaxed">
                                    Select your platform below to see step-by-step instructions on how to get your data.
                                </p>
                            </div>

                            <ScrollArea className="flex-1 -mx-2 px-2">
                                <Accordion type="single" collapsible className="w-full space-y-2">
                                    {DATA_GUIDES.map((guide) => (
                                        <AccordionItem key={guide.id} value={guide.id} className="border border-white/10 rounded-lg bg-zinc-900/50 px-2 overflow-hidden">
                                            <AccordionTrigger className="hover:no-underline py-3 px-2">
                                                <div className="flex items-center gap-3 text-left">
                                                    <div className="p-1.5 rounded-md bg-white/5">
                                                        {guide.icon}
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-medium text-white">{guide.title}</div>
                                                        <div className="text-xs text-zinc-500 font-normal">{guide.description}</div>
                                                    </div>
                                                </div>
                                            </AccordionTrigger>
                                            <AccordionContent className="pb-4 px-2">
                                                <div className="space-y-6 pt-2">
                                                    {guide.steps.map((step, idx) => (
                                                        <div key={idx} className="space-y-2">
                                                            <div className="text-xs font-semibold text-zinc-400 border-l-2 border-primary/50 pl-2">
                                                                {step.label}
                                                            </div>
                                                            <div className="rounded-lg overflow-hidden border border-white/10 bg-black/40">
                                                                <img
                                                                    src={step.img}
                                                                    alt={step.label}
                                                                    className="w-full h-auto object-contain max-h-[600px]"
                                                                    loading="lazy"
                                                                />
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </AccordionContent>
                                        </AccordionItem>
                                    ))}
                                </Accordion>
                            </ScrollArea>
                        </TabsContent>
                    </div>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}
