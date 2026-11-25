<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'users')]
#[ORM\UniqueConstraint(name: 'email', columns: ['email'])]
class User
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\Column(length: 254)]
    public string $email;
    #[ORM\Column(name: 'password_hash', length: 255)]
    public string $passwordHash;
    #[ORM\Column(type: 'json')]
    public array $roles;
    #[ORM\Column(length: 5, options: ['default' => 'en'])]
    public string $locale = 'en';
    #[ORM\Column(type: 'boolean', options: ['default' => false])]
    public bool $disabled = false;
}
