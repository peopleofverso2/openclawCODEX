<?php
/**
 * Pseudo-markdown to HTML converter.
 *
 * Converts simple markdown-like text to clean semantic HTML.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Convert markdown-like text to HTML.
 *
 * Handles: headings (#, ##, ###), unordered lists (- item),
 * ordered lists (1. item), bold, italic, links, and paragraphs.
 *
 * @param string $text Cleaned text with markdown-like formatting.
 * @return string Valid HTML output.
 */
function aif_markdownish_to_html( $text ) {
	$lines  = explode( "\n", $text );
	$html   = '';
	$in_ul  = false;
	$in_ol  = false;
	$p_buf  = [];

	$flush_p = function () use ( &$html, &$p_buf ) {
		if ( ! empty( $p_buf ) ) {
			$content = implode( ' ', $p_buf );
			$content = aif_inline_formatting( $content );
			$html   .= '<p>' . $content . "</p>\n";
			$p_buf   = [];
		}
	};

	$close_list = function () use ( &$html, &$in_ul, &$in_ol ) {
		if ( $in_ul ) {
			$html .= "</ul>\n";
			$in_ul = false;
		}
		if ( $in_ol ) {
			$html .= "</ol>\n";
			$in_ol = false;
		}
	};

	foreach ( $lines as $line ) {
		$l = trim( $line );

		// Blank line: flush paragraph, close list
		if ( '' === $l ) {
			$flush_p();
			$close_list();
			continue;
		}

		// Headings: # -> h2, ## -> h3, ### -> h4
		if ( preg_match( '/^(#{1,3})\s+(.*)$/u', $l, $m ) ) {
			$flush_p();
			$close_list();
			$level   = min( 4, strlen( $m[1] ) + 1 );
			$content = aif_inline_formatting( $m[2] );
			$html   .= "<h{$level}>{$content}</h{$level}>\n";
			continue;
		}

		// Unordered list: "- item" or "* item"
		if ( preg_match( '/^[-*]\s+(.*)$/u', $l, $m ) ) {
			$flush_p();
			if ( $in_ol ) {
				$html .= "</ol>\n";
				$in_ol = false;
			}
			if ( ! $in_ul ) {
				$html .= "<ul>\n";
				$in_ul = true;
			}
			$content = aif_inline_formatting( $m[1] );
			$html   .= "  <li>{$content}</li>\n";
			continue;
		}

		// Ordered list: "1. item", "2. item", etc.
		if ( preg_match( '/^\d+\.\s+(.*)$/u', $l, $m ) ) {
			$flush_p();
			if ( $in_ul ) {
				$html .= "</ul>\n";
				$in_ul = false;
			}
			if ( ! $in_ol ) {
				$html .= "<ol>\n";
				$in_ol = true;
			}
			$content = aif_inline_formatting( $m[1] );
			$html   .= "  <li>{$content}</li>\n";
			continue;
		}

		// Regular text: accumulate into paragraph
		$close_list();
		$p_buf[] = $l;
	}

	// Flush remaining content
	$flush_p();
	$close_list();

	return trim( $html );
}

/**
 * Process inline formatting: bold, italic, inline code, links.
 *
 * @param string $text A single line or paragraph of text.
 * @return string HTML with inline formatting applied.
 */
function aif_inline_formatting( $text ) {
	$t = esc_html( $text );

	// Inline code: `code`
	$t = preg_replace( '/`([^`]+)`/', '<code>$1</code>', $t );

	// Bold: **text**
	$t = preg_replace( '/\*\*([^*]+)\*\*/', '<strong>$1</strong>', $t );

	// Italic: *text*
	$t = preg_replace( '/\*([^*]+)\*/', '<em>$1</em>', $t );

	// Links: [text](url)
	$t = preg_replace_callback(
		'/\[([^\]]+)\]\(([^)]+)\)/',
		function ( $m ) {
			$link_text = $m[1];
			$url       = esc_url( html_entity_decode( $m[2] ) );
			return '<a href="' . $url . '">' . $link_text . '</a>';
		},
		$t
	);

	return $t;
}
