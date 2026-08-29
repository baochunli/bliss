\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{blissbook}[2026/08/29 Semantic LuaLaTeX edition of Bliss]

\LoadClass[
  UTF8,
  zihao=false,
  scheme=plain,
  fontset=none,
  twoside,
  openany
]{ctexbook}

\RequirePackage{fontspec}
\RequirePackage{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{graphicx}
\RequirePackage{multicol}
\RequirePackage{xcolor}
\RequirePackage{hyperref}
\RequirePackage{bookmark}
\RequirePackage{needspace}

% The live InDesign text area is 321 x 535 pt inside a 432 x 648 pt page.
\geometry{
  paperwidth=432bp,
  paperheight=648bp,
  inner=69bp,
  outer=42bp,
  top=43bp,
  bottom=66bp,
  headheight=0bp,
  headsep=0bp,
  footskip=25bp
}

\defaultfontfeatures{Ligatures=TeX}
\setmainfont{MinionPro-Regular.otf}[
  Path=fonts/,
  BoldFont=MinionPro-Bold.otf
]
\setCJKmainfont{FZNewShuSong-Z10.ttf}[
  Path=fonts/,
  BoldFont=FZNewShuSong-Z10.ttf,
  BoldFeatures={FakeBold=2}
]
\setCJKmonofont{FZNewShuSong-Z10.ttf}[Path=fonts/]
\setCJKfamilyfont{blisstitlebyline}{FZNewShuSong-Z10S.ttf}[Path=fonts/]
\newfontfamily\BlissSymbols{AdobeSongStd-Light.otf}[Path=fonts/]
\newfontfamily\BlissColophonCJKSymbols{FZNewShuSong-Z10.ttf}[Path=fonts/]
\newfontfamily\BlissColophonLatin{MinionPro-Regular.otf}[
  Path=fonts/,
  RawFeature={-tlig}
]
% Minion Pro lacks a few Latin Extended tone-mark glyphs used in pinyin.
% TeX Gyre Termes keeps those fallbacks at a normal Latin width.
\newfontfamily\BlissCJKFallback{texgyretermes-regular.otf}
\newcommand{\BlissTitleBylineFont}{\CJKfamily{blisstitlebyline}}

% Hiragino is used by the InDesign edition but was not included by Package.
% Use it when the licensed system font is present; retain a TeX Live fallback.
\IfFontExistsTF{Hiragino Sans GB W6}{
  \setCJKfamilyfont{blissheading}{Hiragino Sans GB W6}
}{
  \setCJKfamilyfont{blissheading}{FandolHei-Bold.otf}
}
% SF Pro Display Bold is the Latin title face of the reference edition and is
% packaged with it. Use the packaged copy so headings match the InDesign book.
\newfontfamily\BlissHeadingLatin{SF-Pro-Display-Bold.otf}[Path=fonts/]
\newcommand{\BlissHeadingFont}{%
  \CJKfamily{blissheading}\BlissHeadingLatin
}

% InDesign's process-black text swatch is 35/31/32 RGB, not device black.
\definecolor{blissink}{HTML}{231F20}

\hypersetup{
  unicode=true,
  pdftitle={幸福},
  pdfauthor={李葆春},
  hidelinks,
  bookmarksnumbered=false
}

\newcommand{\BookBodyFont}{\fontsize{11bp}{16.5bp}\selectfont}
\AtBeginDocument{\color{blissink}\BookBodyFont}
\setlength{\parindent}{22bp}
\setlength{\parskip}{5pt}
\setlength{\columnsep}{22pt}
\tolerance=2000
\emergencystretch=2em
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000

\fancypagestyle{blissbody}{%
  \fancyhf{}
  \fancyfoot[LE,RO]{\fontsize{10bp}{11bp}\selectfont\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}
\pagestyle{blissbody}

\newcommand{\BookLineBreak}{\linebreak}
% Markdown hard breaks are intentional line endings, not requests to stretch
% short lines across the measure as TeX's \linebreak command does.
\newcommand{\BookHardBreak}{\newline}
\newcommand{\BookTab}{\hspace{1em}}
\newcommand{\LatinApostrophe}{\ltjalchar"2019}
\newcommand{\LatinLeftDoubleQuote}{\ltjalchar"201C}
\newcommand{\LatinRightDoubleQuote}{\ltjalchar"201D}
\newcommand{\LatinEmDash}{{\BlissColophonLatin\ltjalchar"2014}}
\newcommand{\CJKPunctuationPairGap}{\kern.5em}
\newcommand{\TextQuote}{{\BlissColophonLatin\ltjalchar34}}
\newcommand{\CJKTimes}{{\BlissColophonCJKSymbols\ltjalchar"00D7}}
\newcommand{\LatinDash}{{\BlissColophonLatin\ltjalchar"2013}}
\newcommand{\BlissCryingEmoji}{（哭）}
\newif\ifBlissFootnoteSeries
\newif\ifBlissAfterSubtitle

\newcommand{\BookParagraph}[1]{%
  \global\BlissFootnoteSeriesfalse
  \ifBlissAfterSubtitle
    \global\BlissAfterSubtitlefalse
    \begingroup
      \clubpenalty=0
      \par\BookBodyFont\noindent\hspace{\parindent}#1\par
    \endgroup
  \else
    \par\BookBodyFont\noindent\hspace{\parindent}#1\par
  \fi
}
\newcommand{\BookQuestion}[1]{\BookParagraph{#1}}
\newcommand{\BookPlainParagraph}[1]{\BookParagraph{#1}}
\newcommand{\BookLeftParagraph}[1]{%
  \global\BlissFootnoteSeriesfalse
  \par\BookBodyFont\noindent #1\par
}
\newcommand{\BookQuote}[1]{%
  \global\BlissFootnoteSeriesfalse
  \par\vspace{5bp}
  \begingroup
    \leftskip=22bp
    \rightskip=22bp
    \parindent=0pt
    \fontsize{10bp}{17bp}\selectfont #1\par
  \endgroup
  \vspace{5bp}
}
\newcommand{\BookImage}[3]{%
  \global\BlissFootnoteSeriesfalse
  % A full-width figure needs room for its following source/date lines; moving
  % it to a fresh page avoids leaving those lines orphaned on an empty page.
  \ifdim#2\linewidth>.9\linewidth\clearpage\fi
  \par\vspace{7bp}
  \begin{center}
    \includegraphics[width=#2\linewidth,height=.9\textheight,keepaspectratio]{#1}%
  \end{center}
  \vspace{7bp}
}
\newcommand{\BookDate}[1]{%
  \global\BlissFootnoteSeriesfalse
  \par\vspace{7bp}\noindent\hfill\BookBodyFont #1\par
}
\newcommand{\BookSubtitle}[1]{%
  \global\BlissFootnoteSeriesfalse
  \par\vspace{14bp}
  \begingroup
    \noindent\hspace{\parindent}%
    \BlissHeadingFont\fontsize{11bp}{18.7bp}\selectfont #1\par
  \endgroup
  \nobreak\vspace{7bp}\nobreak
  \global\BlissAfterSubtitletrue
}
\newcommand{\BookFootnote}[1]{%
  \par
  \ifBlissFootnoteSeries
    \vspace{5bp}%
  \else
    \vspace{18bp}\global\BlissFootnoteSeriestrue
  \fi
  \noindent\fontsize{11bp}{14bp}\selectfont #1\par
  \BookBodyFont
}

\newcommand{\BookColophonRow}[2]{%
  {\BlissHeadingFont #1}& #2\tabularnewline
}
\newcommand{\BookColophonContinuation}[1]{& #1\tabularnewline}
\newcommand{\BookColophonGap}[1]{\noalign{\vskip5bp}}
\newcommand{\BookColophonText}[1]{%
  \multicolumn{2}{@{}l@{}}{#1}\tabularnewline
}
\newcommand{\BookColophon}[1]{%
  \hypersetup{pageanchor=false}
  \pagenumbering{gobble}
  \thispagestyle{empty}\null\clearpage
  \thispagestyle{empty}
  \vspace*{204.5bp}
  \noindent\hspace*{9.6bp}%
  \makebox[0pt][l]{\raisebox{0pt}[0pt][0pt]{\begin{minipage}[t]{333.6bp}
    \hrule height 0.5bp
    \vspace{15bp}
    \begingroup
      \fontsize{9bp}{15.3bp}\selectfont
      \hspace*{1.6bp}%
      \begin{tabular}{@{}l@{\hspace{14bp}}l@{}}
        #1
      \end{tabular}
    \endgroup
    \vspace{17bp}
    \hrule height 0.5bp
  \end{minipage}}}
  \clearpage
}

\newcommand{\BookTitlePage}[4]{%
  \thispagestyle{empty}
  \vspace*{72bp}
  \noindent\hspace*{221bp}%
  \begin{minipage}[t]{50bp}
    \raggedright
    {\BlissHeadingFont\fontsize{40bp}{48bp}\selectfont
      \let\BlissTitleBreak\\%
      \renewcommand{\\}{\BlissTitleBreak[7bp]}%
      #3}
  \end{minipage}
  \par\vspace{155bp}
  \noindent\hspace*{32bp}%
  \begin{minipage}[t]{40bp}
    \centering\BlissTitleBylineFont\fontsize{20bp}{24bp}\selectfont
    #4\\[16bp]著
  \end{minipage}
  \clearpage
  \thispagestyle{empty}\null\clearpage
}

\newcommand{\BookFrontHeading}[1]{%
  \clearpage
  \thispagestyle{empty}
  \vspace*{149bp}
  \noindent\makebox[\textwidth][c]{%
    \hspace*{2.6bp}%
    {\BlissHeadingFont\fontsize{16bp}{20bp}\selectfont #1}
  }\par
  \vspace{39bp}
  \BookBodyFont
}
\newcommand{\BookForeword}[1]{\BookFrontHeading{#1}}
\newcommand{\BookPreface}[1]{%
  \addcontentsline{toc}{part}{#1}%
  \BookFrontHeading{#1}%
}

\makeatletter
\newif\ifBlissFirstTOCPart
\newif\ifBlissPreviousTOCPart
\renewcommand*\l@part[2]{%
  \addpenalty{-\@highpenalty}%
  \ifBlissFirstTOCPart
    \vspace{11bp}%
    \global\BlissFirstTOCPartfalse
  \else
    \ifBlissPreviousTOCPart\vspace{6bp}\else\vspace{19bp}\fi
  \fi
  \noindent{\BlissHeadingFont\fontsize{12bp}{19.4bp}\selectfont #1\par}%
  \vspace{9bp}%
  \global\BlissPreviousTOCParttrue
}
\renewcommand*\l@section[2]{%
  \begingroup
    \raggedright
    \noindent #1\nobreak\hfill\makebox[2.5em][r]{#2}\hspace*{7bp}\par
  \endgroup
  \global\BlissPreviousTOCPartfalse
}
\newcommand{\BookTOC}{%
  \cleardoublepage
  \thispagestyle{empty}
  \vspace*{11bp}
  \begin{center}
    {\BlissHeadingFont\fontsize{16bp}{20bp}\selectfont 目\hspace{1em}录}
  \end{center}
  \vspace{17bp}
  \begingroup
    \global\BlissFirstTOCParttrue
    \global\BlissPreviousTOCPartfalse
    \pagestyle{empty}
    \setlength{\parskip}{0pt}
    \setlength{\columnsep}{43bp}
    \fontsize{11bp}{19.4bp}\selectfont
    \begin{multicols}{2}
      \@starttoc{toc}%
    \end{multicols}
  \endgroup
  \clearpage
  \thispagestyle{empty}\null\clearpage
}
\makeatother

\newcounter{bookpart}
\newcommand{\BookPart}[2]{%
  \cleardoublepage
  \stepcounter{bookpart}
  \phantomsection
  \addcontentsline{toc}{part}{#1}
  \thispagestyle{empty}
  % The eight divider frames use four placements in the InDesign edition.
  % Keep those page-specific placements explicit: the title lengths differ
  % enough that one fixed frame would either drift or clip the longest title.
  \def\BlissPartTop{50bp}%
  \def\BlissPartLeft{214.3bp}%
  \ifcase\value{bookpart}\or
    % 1: defaults
  \or
    % 2: defaults
  \or
    \def\BlissPartTop{46.3bp}\def\BlissPartLeft{208.3bp}%
  \or
    \def\BlissPartTop{46.3bp}\def\BlissPartLeft{210.3bp}%
  \or
    \def\BlissPartTop{24bp}\def\BlissPartLeft{211.3bp}%
  \or
    \def\BlissPartTop{24bp}\def\BlissPartLeft{211.7bp}%
  \or
    \def\BlissPartLeft{212.3bp}%
  \or
    \def\BlissPartTop{26bp}%
  \fi
  \vspace*{\BlissPartTop}
  \noindent\hspace*{\BlissPartLeft}%
  \begin{minipage}[t]{40bp}
    \centering
    {\BlissHeadingFont\fontsize{26bp}{31.15bp}\selectfont
      \let\BlissSavedPartBreak\\%
      \NewDocumentCommand{\BlissPartBreak}{o}{%
        \ifnum\value{bookpart}=1
          \BlissSavedPartBreak[31.15bp]%
        \else
          \IfNoValueTF{##1}
            {\BlissSavedPartBreak}%
            {\BlissSavedPartBreak[31.15bp]}%
        \fi}%
      \let\\\BlissPartBreak
      #2}
  \end{minipage}
  \par
  \clearpage
  \ifnum\value{bookpart}=1
    \hypersetup{pageanchor=true}%
    \pagenumbering{arabic}%
  \fi
}

\newcommand{\BookArticle}[2]{%
  \par
  % Keep the title with at least four body lines while allowing articles to
  % follow one another on the same page.
  \Needspace{140bp}
  \thispagestyle{blissbody}
  \vspace*{15bp}
  \noindent\makebox[\textwidth][c]{%
    \hspace*{2.6bp}%
    \phantomsection
    \addcontentsline{toc}{section}{#2}%
    {\BlissHeadingFont\fontsize{16bp}{21bp}\selectfont #1}
  }\par
  \vspace{15bp}
  \BookBodyFont
}

% Retain two unnumbered closing pages without padding to an absolute page
% number, which could conceal missing content.
\newcommand{\BookFinish}{%
  \clearpage
  \ifnum\value{page}<382
    \ClassError{blissbook}{Book body ended before page 381}{%
      The extracted book may be incomplete; refusing to conceal it with padding.}%
  \fi
  \pagestyle{empty}%
  \thispagestyle{empty}\null\clearpage
  \thispagestyle{empty}\null\clearpage
}
