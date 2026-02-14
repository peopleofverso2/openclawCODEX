<?php
/**
 * Settings page for AI Formatter.
 *
 * Provides configuration for API key, provider, and model.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Register settings page.
 */
add_action( 'admin_menu', function () {
	add_options_page(
		__( 'AI Formatter Settings', 'ai-formatter' ),
		__( 'AI Formatter', 'ai-formatter' ),
		'manage_options',
		'ai-formatter-settings',
		'aif_render_settings_page'
	);
} );

/**
 * Register settings.
 */
add_action( 'admin_init', function () {
	register_setting( 'aif_settings', 'aif_provider', [
		'type'              => 'string',
		'default'           => 'openai',
		'sanitize_callback' => function ( $val ) {
			return in_array( $val, [ 'openai', 'anthropic' ], true ) ? $val : 'openai';
		},
	] );

	register_setting( 'aif_settings', 'aif_api_key', [
		'type'              => 'string',
		'default'           => '',
		'sanitize_callback' => 'sanitize_text_field',
	] );

	register_setting( 'aif_settings', 'aif_model', [
		'type'              => 'string',
		'default'           => '',
		'sanitize_callback' => 'sanitize_text_field',
	] );

	add_settings_section(
		'aif_main',
		__( 'Configuration IA', 'ai-formatter' ),
		function () {
			echo '<p>' . esc_html__( 'Configurez votre fournisseur IA pour activer la correction orthographique et stylistique.', 'ai-formatter' ) . '</p>';
		},
		'ai-formatter-settings'
	);

	add_settings_field(
		'aif_provider',
		__( 'Fournisseur', 'ai-formatter' ),
		function () {
			$val = get_option( 'aif_provider', 'openai' );
			?>
			<select name="aif_provider" id="aif_provider">
				<option value="openai" <?php selected( $val, 'openai' ); ?>>OpenAI</option>
				<option value="anthropic" <?php selected( $val, 'anthropic' ); ?>>Anthropic</option>
			</select>
			<?php
		},
		'ai-formatter-settings',
		'aif_main'
	);

	add_settings_field(
		'aif_api_key',
		__( 'Cle API', 'ai-formatter' ),
		function () {
			$val = get_option( 'aif_api_key', '' );
			$masked = $val ? str_repeat( '*', max( 0, strlen( $val ) - 4 ) ) . substr( $val, -4 ) : '';
			?>
			<input type="password" name="aif_api_key" id="aif_api_key"
				   value="<?php echo esc_attr( $val ); ?>"
				   class="regular-text" autocomplete="off" />
			<?php if ( $masked ) : ?>
				<p class="description"><?php echo esc_html( sprintf( __( 'Cle actuelle : %s', 'ai-formatter' ), $masked ) ); ?></p>
			<?php endif; ?>
			<?php
		},
		'ai-formatter-settings',
		'aif_main'
	);

	add_settings_field(
		'aif_model',
		__( 'Modele', 'ai-formatter' ),
		function () {
			$val = get_option( 'aif_model', '' );
			?>
			<input type="text" name="aif_model" id="aif_model"
				   value="<?php echo esc_attr( $val ); ?>"
				   class="regular-text"
				   placeholder="gpt-4o-mini / claude-sonnet-4-20250514" />
			<p class="description">
				<?php esc_html_e( 'Laissez vide pour le modele par defaut du fournisseur choisi.', 'ai-formatter' ); ?>
			</p>
			<?php
		},
		'ai-formatter-settings',
		'aif_main'
	);
} );

/**
 * Render the settings page.
 */
function aif_render_settings_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	?>
	<div class="wrap">
		<h1><?php esc_html_e( 'AI Formatter - Reglages', 'ai-formatter' ); ?></h1>
		<form method="post" action="options.php">
			<?php
			settings_fields( 'aif_settings' );
			do_settings_sections( 'ai-formatter-settings' );
			submit_button();
			?>
		</form>
	</div>
	<?php
}
