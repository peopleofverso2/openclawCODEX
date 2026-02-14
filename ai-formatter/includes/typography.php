<?php
/**
 * French typography normalization.
 *
 * Applies proper French typographic rules:
 * - Non-breaking spaces before double punctuation
 * - French quotation marks
 * - Curly apostrophes
 * - Em/en dashes
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Narrow no-break space (U+202F) - preferred before ; ? ! in French
if ( ! defined( 'AIF_NNBSP' ) ) {
	define( 'AIF_NNBSP', "\xE2\x80\xAF" );
}
// No-break space (U+00A0)
if ( ! defined( 'AIF_NBSP' ) ) {
	define( 'AIF_NBSP', "\xC2\xA0" );
}

/**
 * Apply French typographic rules to text.
 *
 * @param string $text Input text.
 * @return string Typographically corrected text.
 */
function aif_apply_french_typography( $text ) {
	$t = $text;

	// --- Apostrophes ---
	// Replace straight apostrophes with curly (right single quotation mark U+2019)
	$t = preg_replace( "/(\w)'/u", "$1\xE2\x80\x99", $t );

	// --- Spaces before double punctuation (: ; ? !) ---
	// Remove any existing space(s) before, then add narrow non-breaking space
	$t = preg_replace( '/\h*([;?!])/u', AIF_NNBSP . '$1', $t );
	// Colon gets a regular non-breaking space (French convention)
	$t = preg_replace( '/\h*(:)/u', AIF_NBSP . '$1', $t );

	// --- French quotation marks ---
	// Normalize various quote styles to a neutral double quote first
	$t = preg_replace( '/[\x{201C}\x{201D}\x{201E}\x{201F}\x{00AB}\x{00BB}]/u', '"', $t );
	// Then convert paired "text" to french guillemets with proper spacing
	$t = preg_replace( '/"([^"]+)"/u', "\xC2\xAB" . AIF_NNBSP . '$1' . AIF_NNBSP . "\xC2\xBB", $t );

	// --- Dashes ---
	// Double hyphen -> em dash
	$t = str_replace( '--', "\xE2\x80\x94", $t );
	// Space-hyphen-space (dialogue marker) -> em dash
	$t = preg_replace( '/(?<=\s)-(?=\s)/u', "\xE2\x80\x94", $t );

	// --- Ellipsis ---
	$t = str_replace( '...', "\xE2\x80\xA6", $t );

	// --- Clean up ---
	// Collapse multiple regular spaces (but not non-breaking)
	$t = preg_replace( '/[ \t]{2,}/', ' ', $t );

	// Remove spaces before comma and period
	$t = preg_replace( '/\h+([.,])/u', '$1', $t );

	return $t;
}
