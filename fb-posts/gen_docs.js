const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, HeadingLevel,
  ExternalHyperlink, AlignmentType,
} = require("docx");

const OUT_DIR = __dirname;
const IMG_DIR = path.join(__dirname, "images");

const posts = require("./posts_data.js");

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 200, line: 320 },
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, ...opts })],
  });
}

function metaLine(label, value) {
  return new Paragraph({
    spacing: { after: 80 },
    children: [
      new TextRun({ text: `${label}: `, bold: true }),
      new TextRun({ text: value }),
    ],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true })],
  });
}

function buildDoc(p) {
  const imgBytes = fs.readFileSync(path.join(IMG_DIR, p.img));

  const children = [
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: p.title, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new ImageRun({
        type: "png",
        data: imgBytes,
        transformation: { width: 580, height: 326 },
        altText: { title: p.title, description: p.title, name: p.img },
      })],
    }),
    new Paragraph({ children: [new TextRun("")] }),

    sectionHeading("Thông tin bài"),
    metaLine("Chủ đề", p.category),
    metaLine("Đối tượng đọc", p.audience),
    new Paragraph({ children: [new TextRun("")] }),

    sectionHeading("Mở đầu"),
    para(p.intro),
  ];

  for (const s of p.sections) {
    children.push(sectionHeading(s.heading));
    for (const pgh of s.paragraphs) children.push(para(pgh));
  }

  children.push(sectionHeading("Kết luận"));
  children.push(para(p.conclusion));

  children.push(sectionHeading("Repository"));
  children.push(new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: "Code và ví dụ chạy được tại:" })],
  }));
  children.push(new Paragraph({
    spacing: { after: 200 },
    children: [new ExternalHyperlink({
      children: [new TextRun({ text: p.link, style: "Hyperlink", color: "1155CC", underline: {} })],
      link: p.link,
    })],
  }));
  if (p.tags) {
    children.push(new Paragraph({
      children: [new TextRun({ text: p.tags, color: "888888" })],
    }));
  }

  return new Document({
    creator: "Sophie",
    title: p.title,
    styles: {
      default: { document: { run: { font: "Arial", size: 24 } } },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 36, bold: true, font: "Arial", color: "1F2D5A" },
          paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 },
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: "Arial", color: "1F2D5A" },
          paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 },
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
        },
      },
      children,
    }],
  });
}

(async () => {
  for (const p of posts) {
    const doc = buildDoc(p);
    const buf = await Packer.toBuffer(doc);
    fs.writeFileSync(path.join(OUT_DIR, p.file), buf);
    console.log("wrote", p.file);
  }
})();
